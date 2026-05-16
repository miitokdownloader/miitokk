from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request
import yt_dlp
import os
import uuid
import shutil
import glob
import re
import time
import threading
import subprocess
import requests
from urllib.parse import urlparse

from app_validators import (
    TIKTOK_IMAGE_CDN_SUFFIXES as _TIKTOK_IMAGE_CDN_SUFFIXES,
    PHOTO_FILENAME_RE as _PHOTO_FILENAME_RE,
    ALLOWED_PHOTO_EXTS as _ALLOWED_PHOTO_EXTS,
    is_valid_tiktok_image_url as _is_valid_tiktok_image_url,
    is_valid_photo_filename as _is_valid_photo_filename,
)

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
# Client IP helper
# ---------------------------------------------------------------------------
# NOTE: X-Forwarded-For is trusted unconditionally here.
# If deployed without a trusted reverse proxy, use Flask's ProxyFix middleware
# with x_for=1 to restrict header trust to one hop. This single helper is the
# canonical way to derive the per-IP rate-limit key, so the trust boundary is
# documented and enforced in exactly one place rather than copy-pasted.
def _client_ip(req):
    return (req.headers.get('X-Forwarded-For', req.remote_addr or '')
            .split(',')[0].strip())


# TikTok image-CDN allowlist used by /photo-proxy and /download-photo. The
# allowlist itself, the photo-filename regex, and the helper that validates
# image URLs all live in app_validators.py so they can be unit-tested without
# importing Flask. They are imported above and re-bound here under their
# original module-level names so the rest of this file (and any code that
# previously imported them from app.py) keeps working unchanged.


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------
# CSP rationale: img-src already permits 'data: https:' which covers the
# inline thumbnails/photos rendered through /photo-proxy (same-origin) plus
# any https:// fallbacks. connect-src 'self' is sufficient because the
# frontend only XHR/fetches our own endpoints (/preview, /download, /photos,
# /photo-proxy, /download-photo). The PHOTO mode does not introduce any new
# external host, so CSP does not need to be widened.
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

    # Rate limiting (uses the shared _client_ip helper which carries the
    # X-Forwarded-For trust caveat).
    client_ip = _client_ip(request)
    if not _check_rate_limit(client_ip, _rate_store_download):
        return jsonify({'error': 'Terlalu cepat, coba lagi beberapa saat'}), 429

    tmp_id = str(uuid.uuid4())

    try:
        # Check ffmpeg availability
        ffmpeg_bin = shutil.which('ffmpeg')
        if not ffmpeg_bin:
            return jsonify({'error': 'ffmpeg tidak tersedia di server. Hubungi admin.'}), 500

        # Step 1: Download raw video with yt-dlp
        raw_outtmpl = f"/tmp/{tmp_id}_raw.%(ext)s"
        ydl_opts = {
            'outtmpl': raw_outtmpl,
            'format': 'best[ext=mp4]/best',
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Step 2: Find the downloaded raw file
        raw_candidates = glob.glob(f"/tmp/{tmp_id}_raw.*")
        if not raw_candidates:
            return jsonify({'error': 'File video tidak ditemukan setelah download'}), 500
        raw_file = raw_candidates[0]

        # Step 3: Run ffmpeg to convert to a WhatsApp/Android-compatible MP4
        output_path = f"/tmp/{tmp_id}_out.mp4"

        if quality == '720':
            ffmpeg_cmd = [
                ffmpeg_bin, '-y', '-i', raw_file,
                '-vf', 'scale=-2:720',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                output_path,
            ]
        elif quality == '1080':
            ffmpeg_cmd = [
                ffmpeg_bin, '-y', '-i', raw_file,
                '-vf', 'scale=-2:1080',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                output_path,
            ]
        else:  # best
            ffmpeg_cmd = [
                ffmpeg_bin, '-y', '-i', raw_file,
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '128k',
                '-movflags', '+faststart',
                output_path,
            ]

        result = subprocess.run(ffmpeg_cmd, capture_output=True)
        if result.returncode != 0:
            # Clean up raw file before returning error
            try:
                os.remove(raw_file)
            except Exception:
                pass
            return jsonify({'error': 'Konversi video gagal. Coba lagi.'}), 500

        @after_this_request
        def cleanup_video(response):
            try:
                os.remove(raw_file)
            except Exception:
                pass
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

    # Rate limiting (per-IP, separate store from /download). Uses the same
    # _client_ip helper so the X-Forwarded-For trust caveat documented there
    # applies here too.
    client_ip = _client_ip(request)
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
            return jsonify({'error': 'Konten ini bukan slideshow/foto.'}), 400

        # Detect slideshow: yt-dlp returns _type=='playlist' for image
        # slideshows, with each entry being one image. Some extractors
        # represent it differently, so we also fall back to scanning entries
        # for image-like URLs.
        entries = info.get('entries') or []
        if info.get('_type') != 'playlist' and not entries:
            return jsonify({'error': 'Konten ini bukan slideshow/foto.'}), 400

        photo_urls = []
        seen = set()

        def _is_image_url(candidate):
            if not candidate or not isinstance(candidate, str):
                return False
            lowered = candidate.lower().split('?', 1)[0]
            return lowered.endswith(_ALLOWED_PHOTO_EXTS) or lowered.endswith('.heic')

        def _add(candidate):
            if candidate and candidate not in seen:
                seen.add(candidate)
                photo_urls.append(candidate)

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            entry_url = entry.get('url')
            if _is_image_url(entry_url):
                _add(entry_url)
                continue
            # Fall back to the largest thumbnail
            thumbs = entry.get('thumbnails') or []
            if thumbs:
                last = thumbs[-1]
                if isinstance(last, dict):
                    _add(last.get('url'))

        if not photo_urls:
            return jsonify({'error': 'Konten ini bukan slideshow/foto.'}), 400

        return jsonify({
            'photos': photo_urls,
            'count': len(photo_urls),
            'title': (info.get('title') or '')[:80],
            'uploader': info.get('uploader') or '',
            'thumbnail': info.get('thumbnail') or '',
        })

    except Exception:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


@app.route('/photo-proxy')
def photo_proxy():
    url = (request.args.get('url') or '').strip()
    if not url or not _is_valid_tiktok_image_url(url):
        return jsonify({'error': 'Invalid host'}), 400

    try:
        # allow_redirects=False: a 3xx Location pointing at an internal
        # address (RFC1918, 169.254.169.254 cloud metadata, etc.) would
        # bypass the host allowlist if we let requests follow it, so refuse
        # 3xx outright. The legitimate TikTok image-CDN URLs we care about
        # respond 200 directly.
        upstream = requests.get(
            url,
            stream=True,
            timeout=15,
            allow_redirects=False,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://www.tiktok.com/',
            },
        )
        if 300 <= upstream.status_code < 400:
            try:
                upstream.close()
            except Exception:
                pass
            return jsonify({'error': 'Gagal mengambil gambar'}), 502
        if upstream.status_code != 200:
            # stream=True keeps the underlying TCP connection open until the
            # response object is closed or GC'd. Close explicitly on the
            # error path to avoid a slow file-descriptor leak under load.
            try:
                upstream.close()
            except Exception:
                pass
            return jsonify({'error': 'Gagal mengambil gambar'}), 502

        mimetype = upstream.headers.get('Content-Type', 'image/jpeg').split(';', 1)[0].strip() or 'image/jpeg'

        def _stream():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        resp = Response(_stream(), mimetype=mimetype)
        resp.headers['Cache-Control'] = 'public, max-age=86400'
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    except Exception:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


@app.route('/download-photo')
def download_photo():
    url = (request.args.get('url') or '').strip()
    filename = (request.args.get('filename') or '').strip()

    if not url or not _is_valid_tiktok_image_url(url):
        return jsonify({'error': 'Invalid host'}), 400

    # Strict filename validation: must be present, match the safe pattern AND
    # carry an allowed image extension. We refuse missing/invalid filenames
    # with 400 instead of falling back to a constant default, because a
    # constant default would collide across photos in the bulk-download
    # flow (every download would overwrite 'miitok_photo.jpg').
    if not _is_valid_photo_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400
    safe_name = filename

    try:
        # Same redirect-defense as /photo-proxy: a 3xx response could
        # smuggle the request to an internal host outside the allowlist.
        upstream = requests.get(
            url,
            stream=True,
            timeout=15,
            allow_redirects=False,
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://www.tiktok.com/',
            },
        )
        if 300 <= upstream.status_code < 400:
            try:
                upstream.close()
            except Exception:
                pass
            return jsonify({'error': 'Gagal mengambil gambar'}), 502
        if upstream.status_code != 200:
            # See /photo-proxy: explicit close to release the streaming
            # connection on the error path.
            try:
                upstream.close()
            except Exception:
                pass
            return jsonify({'error': 'Gagal mengambil gambar'}), 502

        mimetype = upstream.headers.get('Content-Type', 'image/jpeg').split(';', 1)[0].strip() or 'image/jpeg'

        def _stream():
            try:
                for chunk in upstream.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        resp = Response(_stream(), mimetype=mimetype)
        resp.headers['Content-Disposition'] = f'attachment; filename="{safe_name}"'
        resp.headers['Cache-Control'] = 'no-store'
        return resp

    except Exception:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
