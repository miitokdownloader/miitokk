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
from urllib.parse import urlparse

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Log ffmpeg availability at startup (works with both gunicorn and direct run)
_ffmpeg_startup_path = shutil.which("ffmpeg")
if _ffmpeg_startup_path:
    print(f"[startup] ffmpeg found: {_ffmpeg_startup_path}", flush=True)
    _ffmpeg_version_result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print(f"[startup] ffmpeg version output: {_ffmpeg_version_result.stdout.splitlines()[0] if _ffmpeg_version_result.stdout else 'unknown'}", flush=True)
else:
    print("[startup] WARNING: ffmpeg NOT found. Video conversion will not work.", flush=True)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
_rate_lock = threading.Lock()
_rate_store_download = {}  # {ip: last_request_timestamp} for /download
_rate_store_photos = {}    # {ip: last_request_timestamp} for /photos
_rate_store_proxy = {}     # {ip: last_request_timestamp} for /photo-proxy & /download-photo
RATE_LIMIT_SECONDS = 10
RATE_LIMIT_PROXY_SECONDS = 1  # Allow 1 request per second per IP for proxy


def _check_rate_limit(ip, store):
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    with _rate_lock:
        last = store.get(ip)
        if last is not None and (now - last) < RATE_LIMIT_SECONDS:
            return False
        store[ip] = now
        return True


def _check_proxy_rate_limit(ip):
    """Lightweight rate limit for proxy endpoints - 1 req/sec."""
    now = time.time()
    with _rate_lock:
        last = _rate_store_proxy.get(ip)
        if last is not None and (now - last) < RATE_LIMIT_PROXY_SECONDS:
            return False
        _rate_store_proxy[ip] = now
        return True


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------
TIKTOK_DOMAINS = {'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com', 'www.tiktok.com'}

# Allowed CDN domains for photo proxy (to prevent SSRF)
ALLOWED_CDN_SUFFIXES = (
    '.tiktokcdn.com',
    '.tiktokcdn-us.com',
    '.musical.ly',
    '.muscdn.com',
    '.tiktok.com',
    '.ibytedtos.com',
    '.ipstatp.com',
)


def _is_allowed_cdn_url(url):
    """Check that a URL is HTTPS and points to an allowed TikTok CDN domain."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != 'https':
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname = hostname.lower()
        for suffix in ALLOWED_CDN_SUFFIXES:
            if hostname == suffix.lstrip('.') or hostname.endswith(suffix):
                return True
        return False
    except Exception:
        return False


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
        # Check ffmpeg availability
        ffmpeg_bin = shutil.which('ffmpeg')
        if not ffmpeg_bin:
            return jsonify({'error': 'Server belum support FFmpeg. Periksa nixpacks.toml dan redeploy.'}), 500

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
        return jsonify({'error': 'Masukkan link TikTok dulu'}), 400

    if not _is_valid_tiktok_url(url):
        return jsonify({'error': 'URL tidak valid atau bukan link TikTok'}), 400

    # Rate limiting
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
            return jsonify({'error': 'Tidak bisa mengambil info dari URL ini'}), 400

        # Check if it's a slideshow/photo post
        photo_urls = []

        if info.get('_type') == 'playlist' and info.get('entries'):
            # It's a slideshow - extract image URLs from entries
            for entry in info['entries']:
                if entry and entry.get('url'):
                    photo_urls.append(entry['url'])
                elif entry and entry.get('thumbnails'):
                    # Some versions put the image in thumbnails
                    for thumb in entry['thumbnails']:
                        if thumb.get('url'):
                            photo_urls.append(thumb['url'])
                            break
        elif info.get('thumbnails'):
            # Try to find images in format list or thumbnails for single-image posts
            formats = info.get('formats', [])
            for fmt in formats:
                if fmt.get('vcodec') == 'none' and fmt.get('acodec') == 'none':
                    if fmt.get('url') and any(ext in fmt.get('url', '') for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        photo_urls.append(fmt['url'])

        if not photo_urls:
            return jsonify({'error': 'Foto tidak ditemukan atau link bukan slideshow.'}), 400

        result = {
            'photos': photo_urls,
            'count': len(photo_urls),
        }
        if info.get('title'):
            result['title'] = info['title'][:80]
        if info.get('uploader'):
            result['uploader'] = info['uploader']
        if info.get('thumbnail'):
            result['thumbnail'] = info['thumbnail']

        return jsonify(result)

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if 'Sign in' in msg or 'login' in msg.lower():
            return jsonify({'error': 'Konten ini memerlukan login TikTok'}), 500
        return jsonify({'error': 'Gagal mengambil foto. Pastikan link valid dan coba lagi.'}), 500
    except Exception:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


@app.route('/photo-proxy')
def photo_proxy():
    import requests as req_lib

    url = request.args.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL parameter required'}), 400

    # Validate URL against CDN allowlist (SSRF protection)
    if not _is_allowed_cdn_url(url):
        return jsonify({'error': 'Invalid URL'}), 400

    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Too many requests'}), 429

    MAX_PROXY_BYTES = 20 * 1024 * 1024  # 20 MB

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        resp = req_lib.get(url, headers=headers, timeout=15, stream=True, allow_redirects=False)

        if resp.status_code != 200:
            return '', 502

        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        # Ensure it's actually an image
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'

        def generate():
            bytes_sent = 0
            for chunk in resp.iter_content(chunk_size=8192):
                bytes_sent += len(chunk)
                if bytes_sent > MAX_PROXY_BYTES:
                    break
                yield chunk

        return Response(
            generate(),
            content_type=content_type,
            headers={
                'Cache-Control': 'public, max-age=86400',
                'Access-Control-Allow-Origin': '*',
            }
        )
    except Exception:
        return '', 502


@app.route('/download-photo')
def download_photo():
    import requests as req_lib

    url = request.args.get('url', '').strip()
    filename = request.args.get('filename', 'miitok_photo.jpg').strip()

    if not url:
        return jsonify({'error': 'URL parameter required'}), 400

    # Validate URL against CDN allowlist (SSRF protection)
    if not _is_allowed_cdn_url(url):
        return jsonify({'error': 'Invalid URL'}), 400

    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_proxy_rate_limit(client_ip):
        return jsonify({'error': 'Too many requests'}), 429

    # Sanitize filename
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    if not filename.endswith(('.jpg', '.jpeg', '.png', '.webp')):
        filename += '.jpg'

    MAX_PROXY_BYTES = 20 * 1024 * 1024  # 20 MB

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        resp = req_lib.get(url, headers=headers, timeout=15, stream=True, allow_redirects=False)

        if resp.status_code != 200:
            return jsonify({'error': 'Gagal mengunduh foto'}), 502

        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        if not content_type.startswith('image/'):
            content_type = 'image/jpeg'

        def generate():
            bytes_sent = 0
            for chunk in resp.iter_content(chunk_size=8192):
                bytes_sent += len(chunk)
                if bytes_sent > MAX_PROXY_BYTES:
                    break
                yield chunk

        return Response(
            generate(),
            content_type=content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Access-Control-Allow-Origin': '*',
            }
        )
    except Exception:
        return jsonify({'error': 'Gagal mengunduh foto'}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
