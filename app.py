from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request
import yt_dlp
import os
import uuid
import shutil
import glob
import re
import time
import threading
from urllib.parse import urlparse

app = Flask(__name__, static_folder='static', static_url_path='/static')

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_rate_store_download = {}  # {ip: last_request_timestamp} for /download
_rate_store_photos = {}    # {ip: last_request_timestamp} for /photos
RATE_LIMIT_SECONDS = 10


def _check_rate_limit(ip, store):
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    with _rate_lock:
        last = store.get(ip)
        if last is not None and (now - last) < RATE_LIMIT_SECONDS:
            return False
        store[ip] = now
        return True


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------
TIKTOK_DOMAINS = {'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com', 'www.tiktok.com'}


def _is_valid_tiktok_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        host = parsed.netloc.lower()
        # Strip port if present
        host = host.split(':')[0]
        return host in TIKTOK_DOMAINS
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self'; "
        "img-src 'self' data: https:; "
        "media-src 'self' blob:;"
    )
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/static/makima.mp4')
def serve_video():
    video_path = os.path.join(app.static_folder, 'makima.mp4')
    if not os.path.exists(video_path):
        return '', 404
    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)
    if range_header:
        try:
            byte_start = int(range_header.replace('bytes=', '').split('-')[0])
            byte_end = min(byte_start + 1024 * 1024, file_size - 1)
            length = byte_end - byte_start + 1
            with open(video_path, 'rb') as f:
                f.seek(byte_start)
                data = f.read(length)
            rv = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
            rv.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
            rv.headers.add('Accept-Ranges', 'bytes')
            rv.headers.add('Content-Length', str(length))
            return rv
        except Exception:
            pass
    return send_file(video_path, mimetype='video/mp4')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/preview', methods=['POST'])
def preview():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
    else:
        url = (request.form.get('url') or '').strip()

    if not url:
        return jsonify({'error': 'URL kosong'}), 400

    if not _is_valid_tiktok_url(url):
        return jsonify({'error': 'URL tidak valid atau bukan link TikTok'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({'error': 'Tidak bisa ambil info'}), 400

        # Hanya return data asli yang tersedia
        result = {}
        if info.get('title'):
            result['title'] = info['title'][:80]
        if info.get('thumbnail'):
            result['thumbnail'] = info['thumbnail']
        if info.get('duration'):
            result['duration'] = int(info['duration'])
        if info.get('uploader'):
            result['uploader'] = info['uploader']
        if info.get('webpage_url'):
            result['webpage_url'] = info['webpage_url']

        # Cek apakah foto/slideshow
        if info.get('_type') == 'playlist':
            result['is_slideshow'] = True

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


@app.route('/download', methods=['POST'])
def download():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
        quality = data.get('quality', '').strip()
    else:
        url = (request.form.get('url') or '').strip()
        quality = (request.form.get('quality') or '').strip()

    print(f"[download] url={url!r} quality={quality!r}", flush=True)

    if not url:
        return jsonify({'error': 'Masukkan link TikTok dulu'}), 400

    if not _is_valid_tiktok_url(url):
        return jsonify({'error': 'URL tidak valid atau bukan link TikTok'}), 400

    # Quality validation
    valid_qualities = {'best', '1080', '720'}
    if not quality:
        quality = 'best'
    elif quality not in valid_qualities:
        return jsonify({'error': 'Kualitas tidak valid'}), 400

    # Lightweight probe: reject slideshow/playlist before attempting video download
    try:
        _probe_opts = {'quiet': True, 'skip_download': True, 'noplaylist': False}
        with yt_dlp.YoutubeDL(_probe_opts) as _ydl:
            _probe = _ydl.extract_info(url, download=False)
        if _probe and _probe.get('_type') == 'playlist':
            return jsonify({'error': 'Ini konten foto/slideshow. Gunakan tab PHOTO untuk mengunduh.'}), 400
    except Exception:
        pass  # If probe fails, let the download attempt proceed and surface its own error

    # Rate limiting
    # NOTE: X-Forwarded-For is trusted unconditionally here.
    # If deployed without a trusted reverse proxy, use Flask's ProxyFix middleware
    # with x_for=1 to restrict header trust to one hop.
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_rate_limit(client_ip, _rate_store_download):
        return jsonify({'error': 'Terlalu cepat, coba lagi beberapa saat'}), 429

    tmp_id = str(uuid.uuid4())

    try:
        format_map = {
            'best': 'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4][vcodec^=avc1]/best[ext=mp4]/best',
            '1080': 'bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4][vcodec^=avc1]/best[height<=1080][ext=mp4]/best[ext=mp4]',
            '720':  'bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[height<=720][ext=mp4][vcodec^=avc1]/best[height<=720][ext=mp4]/best[ext=mp4]',
        }

        output_path = f"/tmp/{tmp_id}.mp4"

        _ffmpeg_bin = shutil.which('ffmpeg')
        ffmpeg_dir = os.path.dirname(_ffmpeg_bin) if _ffmpeg_bin else None
        ydl_opts = {
            'outtmpl': output_path,
            'format': format_map.get(quality, format_map['best']),
            'merge_output_format': 'mp4',
            'postprocessors': [{'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4'}],  # NOTE: yt-dlp uses single-r spelling (library's own typo)
            'postprocessor_args': {'ffmpeg': ['-c:v', 'libx264', '-c:a', 'aac', '-movflags', '+faststart']},
            'fixup': 'force',
            'quiet': True,
        }
        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(output_path):
            candidates = glob.glob(f"/tmp/{tmp_id}.*")
            output_path = candidates[0] if candidates else None

        if not output_path:
            for f in glob.glob(f"/tmp/{tmp_id}.*"):
                try:
                    os.remove(f)
                except Exception:
                    pass
            return jsonify({'error': 'File video tidak ditemukan setelah download'}), 500

        @after_this_request
        def cleanup_video(response):
            try:
                os.remove(output_path)
            except Exception:
                pass
            return response

        return send_file(output_path, as_attachment=True, download_name='miitok_video.mp4', mimetype='video/mp4')

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if 'Sign in' in msg or 'login' in msg.lower():
            return jsonify({'error': 'Video ini memerlukan login TikTok'}), 500
        return jsonify({'error': 'Download gagal. Pastikan link valid dan coba lagi.'}), 500
    except Exception as e:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


@app.route('/photos', methods=['POST'])
def photos():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
    else:
        url = (request.form.get('url') or '').strip()

    if not url:
        return jsonify({'error': 'URL kosong'}), 400

    if not _is_valid_tiktok_url(url):
        return jsonify({'error': 'URL tidak valid atau bukan link TikTok'}), 400

    # Rate limiting
    # NOTE: X-Forwarded-For is trusted unconditionally here.
    # If deployed without a trusted reverse proxy, use Flask's ProxyFix middleware
    # with x_for=1 to restrict header trust to one hop.
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_rate_limit(client_ip, _rate_store_photos):
        return jsonify({'error': 'Terlalu cepat, coba lagi beberapa saat'}), 429

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            return jsonify({'photos': [], 'images': [], 'count': 0, 'title': '', 'type': 'photo'}), 200

        photo_urls = []

        # Helper: pick best thumbnail from a list
        def best_thumbnail(thumbnails):
            if not thumbnails:
                return None
            valid = [t for t in thumbnails if t.get('url', '').startswith('https://')]
            if not valid:
                return None
            return max(valid, key=lambda t: (t.get('width') or 0) * (t.get('height') or 0), default=None)

        # Check top-level 'images' key (some yt-dlp versions)
        # Each item may be a dict with url/width/height for one slide at one resolution
        # Group by picking highest-res: deduplicate by collecting all dicts, sort by area desc
        # then add only if the URL hasn't been seen (to avoid adding multiple sizes of same slide)
        if info.get('images'):
            imgs_raw = info['images']
            dicts = [i for i in imgs_raw if isinstance(i, dict) and i.get('url', '').startswith('https://')]
            strings = [str(i) for i in imgs_raw if not isinstance(i, dict) and str(i).startswith('https://')]
            if dicts:
                # NOTE: If TikTok returns multiple resolution variants with distinct CDN URLs,
                # all will be included here. The playlist-entry branch (below) handles this
                # correctly per-entry. This path is used only for older yt-dlp that returns
                # top-level 'images' without per-entry granularity.
                # Sort by resolution descending
                dicts_sorted = sorted(dicts, key=lambda i: (i.get('width') or 0) * (i.get('height') or 0), reverse=True)
                seen_urls = set()
                for img in dicts_sorted:
                    u = img.get('url', '')
                    if u and u not in seen_urls:
                        photo_urls.append(u)
                        seen_urls.add(u)
            else:
                photo_urls.extend(strings)

        # Check playlist entries (TikTok slideshow)
        if not photo_urls and info.get('_type') == 'playlist' and info.get('entries'):
            for entry in (info['entries'] or []):
                if not entry:
                    continue
                added = False

                # 1. Try 'images' key on entry
                if entry.get('images'):
                    imgs = entry['images']
                    # Sort by resolution descending and pick highest-res
                    dicts = [i for i in imgs if isinstance(i, dict)]
                    if dicts:
                        best = sorted(dicts, key=lambda i: (i.get('width') or 0) * (i.get('height') or 0), reverse=True)[0]
                        u = best.get('url', '')
                    else:
                        u = str(imgs[0]) if imgs else ''
                    if u.startswith('https://'):
                        photo_urls.append(u)
                        added = True

                # 2. Try formats - look for image-like extensions
                if not added:
                    for fmt in (entry.get('formats') or []):
                        ext = fmt.get('ext', '')
                        fmt_url = fmt.get('url', '')
                        if fmt_url.startswith('https://') and ext in ('jpg', 'jpeg', 'png', 'webp'):
                            photo_urls.append(fmt_url)
                            added = True
                            break

                # 3. Try direct URL if it looks like an image host
                if not added:
                    direct = entry.get('url', '')
                    if direct.startswith('https://') and any(ext in direct.lower() for ext in ['.jpg', '.jpeg', '.webp', '.png']):
                        photo_urls.append(direct)
                        added = True

                # 4. Fall back to highest-res thumbnail
                if not added:
                    thumb = best_thumbnail(entry.get('thumbnails') or [])
                    if thumb:
                        photo_urls.append(thumb['url'])

        if not photo_urls:
            return jsonify({'error': 'Tidak ada foto ditemukan. Link ini mungkin video, bukan slideshow.'}), 400

        title = info.get('title', '')
        uploader = info.get('uploader', '')
        thumbnail = info.get('thumbnail', '')

        return jsonify({
            'type': 'photo',
            'photos': photo_urls,
            'images': photo_urls,
            'count': len(photo_urls),
            'title': title,
            'uploader': uploader,
            'thumbnail': thumbnail,
        })

    except Exception as e:
        return jsonify({'error': 'Gagal mengambil foto, coba lagi'}), 500


@app.route('/photo-proxy')
def photo_proxy():
    import requests as req_lib
    target_url = request.args.get('url', '').strip()
    if not target_url or not target_url.startswith('https://'):
        return '', 400
    _parsed_host = urlparse(target_url).netloc.lower().split(':')[0]
    _ALLOWED_TIKTOK_HOSTS = (
        'tiktokcdn.com', 'tiktokcdn-us.com', 'tiktokv.com', 'tiktok.com',
    )
    if not any(_parsed_host == h or _parsed_host.endswith('.' + h) for h in _ALLOWED_TIKTOK_HOSTS):
        return '', 403
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
            'Referer': 'https://www.tiktok.com/',
        }
        r = req_lib.get(target_url, headers=headers, timeout=15, stream=True)
        if r.status_code != 200:
            return '', 404
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'application/octet-stream'
        return Response(r.content, status=200, mimetype=content_type)
    except Exception:
        return '', 404


@app.route('/download-photo')
def download_photo():
    import requests as req_lib
    target_url = request.args.get('url', '').strip()
    filename = request.args.get('filename', 'miitok_photo.jpg').strip()

    # Sanitize filename
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    if not filename:
        filename = 'miitok_photo.jpg'

    if not target_url or not target_url.startswith('https://'):
        return '', 400

    _parsed_host = urlparse(target_url).netloc.lower().split(':')[0]
    _ALLOWED_TIKTOK_HOSTS = (
        'tiktokcdn.com', 'tiktokcdn-us.com', 'tiktokv.com', 'tiktok.com',
        'p16-sign.tiktokcdn-us.com', 'p77-sign.tiktokcdn-us.com',
    )
    if not any(_parsed_host == h or _parsed_host.endswith('.' + h) for h in _ALLOWED_TIKTOK_HOSTS):
        return '', 403

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
            'Referer': 'https://www.tiktok.com/',
        }
        r = req_lib.get(target_url, headers=headers, timeout=15, stream=True)
        if r.status_code != 200:
            return '', 404
        content_type = r.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'

        response = Response(r.content, status=200, mimetype=content_type)
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        return '', 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
