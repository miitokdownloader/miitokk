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
_rate_store = {}  # {ip: last_request_timestamp}
RATE_LIMIT_SECONDS = 10


def _check_rate_limit(ip):
    """Return True if the request is allowed, False if rate-limited."""
    now = time.time()
    with _rate_lock:
        last = _rate_store.get(ip)
        if last is not None and (now - last) < RATE_LIMIT_SECONDS:
            return False
        _rate_store[ip] = now
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
        "style-src 'self' 'unsafe-inline'; "
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
    valid_qualities = {'best', '1080', '720', 'audio'}
    if not quality:
        quality = 'best'
    elif quality not in valid_qualities:
        return jsonify({'error': 'Kualitas tidak valid'}), 400

    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if not _check_rate_limit(client_ip):
        return jsonify({'error': 'Terlalu cepat, coba lagi beberapa saat'}), 429

    tmp_id = str(uuid.uuid4())

    try:
        if quality == 'audio':
            ffmpeg_path = shutil.which('ffmpeg')
            ffprobe_path = shutil.which('ffprobe')
            print(f"[audio] ffmpeg={ffmpeg_path} ffprobe={ffprobe_path}", flush=True)

            if not ffmpeg_path or not ffprobe_path:
                return jsonify({'error': 'MP3 conversion requires FFmpeg on the server.'}), 500

            audio_base = f"/tmp/{tmp_id}"

            ydl_opts = {
                'outtmpl': audio_base + '.%(ext)s',
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'ffmpeg_location': os.path.dirname(ffmpeg_path),
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            audio_path = audio_base + '.mp3'
            if not os.path.exists(audio_path):
                # fallback: find any file with this base name
                candidates = [f for f in glob.glob(audio_base + '.*') if f.endswith('.mp3')]
                if not candidates:
                    candidates = glob.glob(audio_base + '.*')
                audio_path = candidates[0] if candidates else None

            if not audio_path or not os.path.exists(audio_path):
                for f in glob.glob(audio_base + '.*'):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                return jsonify({'error': 'File audio tidak ditemukan'}), 500

            dl_name = 'miitok_audio.mp3'

            @after_this_request
            def cleanup_audio(response):
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
                return response

            return send_file(audio_path, mimetype='audio/mpeg', as_attachment=True, download_name=dl_name)

        else:
            format_map = {
                'best': 'bestvideo+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                '720':  'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            }

            output_path = f"/tmp/{tmp_id}.mp4"

            # Cek preview dulu (tanpa download)
            check_opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(check_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info.get('_type') == 'playlist':
                for f in glob.glob(f"/tmp/{tmp_id}.*"):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
                return jsonify({'error': 'Ini konten foto/slideshow, tidak bisa didownload sebagai video'}), 400

            ydl_opts = {
                'outtmpl': output_path,
                'format': format_map.get(quality, 'best'),
                'merge_output_format': 'mp4',
            }

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

            return send_file(output_path, as_attachment=True, download_name='miitok_video.mp4')

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if 'Sign in' in msg or 'login' in msg.lower():
            return jsonify({'error': 'Video ini memerlukan login TikTok'}), 500
        return jsonify({'error': 'Download gagal. Pastikan link valid dan coba lagi.'}), 500
    except Exception as e:
        return jsonify({'error': 'Terjadi kesalahan, coba lagi'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
