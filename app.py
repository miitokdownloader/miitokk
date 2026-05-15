from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request
import yt_dlp
import os
import uuid
import shutil
import glob

app = Flask(__name__, static_folder='static', static_url_path='/static')

@app.route('/static/makima.mp4')
def serve_video():
    video_path = os.path.join(app.static_folder, 'makima.mp4')
    if not os.path.exists(video_path):
        return '', 404
    file_size = os.path.getsize(video_path)
    range_header = request.headers.get('Range', None)
    if range_header:
        byte_start = int(range_header.replace('bytes=', '').split('-')[0])
        byte_end = min(byte_start + 1024*1024, file_size - 1)
        length = byte_end - byte_start + 1
        with open(video_path, 'rb') as f:
            f.seek(byte_start)
            data = f.read(length)
        rv = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
        rv.headers.add('Content-Range', f'bytes {byte_start}-{byte_end}/{file_size}')
        rv.headers.add('Accept-Ranges', 'bytes')
        rv.headers.add('Content-Length', str(length))
        return rv
    return send_file(video_path, mimetype='video/mp4')

@app.route('/')
def index():
    return render_template('index.html')

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
    if not quality:
        quality = 'best'

    tmp_id = str(uuid.uuid4())

    try:
        if quality == 'audio':
            ffmpeg_path = shutil.which('ffmpeg')
            ffprobe_path = shutil.which('ffprobe')
            print(f"[audio] ffmpeg={ffmpeg_path} ffprobe={ffprobe_path}", flush=True)

            if not ffmpeg_path:
                return jsonify({'error': 'FFmpeg tidak tersedia di server. Coba kualitas lain.'}), 500

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

            # Cari file hasil output
            audio_path = audio_base + '.mp3'
            if not os.path.exists(audio_path):
                candidates = glob.glob(audio_base + '.*')
                if candidates:
                    audio_path = candidates[0]
                else:
                    return jsonify({'error': 'File audio tidak ditemukan setelah download'}), 500

            @after_this_request
            def cleanup_audio(response):
                try: os.remove(audio_path)
                except: pass
                return response

            return send_file(audio_path, as_attachment=True, download_name='miitok_audio.mp3')

        else:
            format_map = {
                'best': 'bestvideo+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
                '720':  'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            }

            output_path = f"/tmp/{tmp_id}.mp4"

            # Cek dulu apakah foto/slideshow tanpa download
            check_opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(check_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Kalau slideshow/foto
            if info.get('_type') == 'playlist' or 'images' in str(info.get('formats', '')):
                photo_urls = []
                entries = info.get('entries') or []
                for entry in entries:
                    thumb = entry.get('thumbnail') or entry.get('url')
                    if thumb:
                        photo_urls.append(thumb)
                if photo_urls:
                    return jsonify({'type': 'photos', 'urls': photo_urls})
                return jsonify({'error': 'Slideshow foto tidak dapat diproses'}), 400

            ydl_opts = {
                'outtmpl': output_path,
                'format': format_map.get(quality, 'best'),
                'merge_output_format': 'mp4',
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            if not os.path.exists(output_path):
                candidates = glob.glob(f"/tmp/{tmp_id}.*")
                if candidates:
                    output_path = candidates[0]
                else:
                    return jsonify({'error': 'File video tidak ditemukan setelah download'}), 500

            @after_this_request
            def cleanup_video(response):
                try: os.remove(output_path)
                except: pass
                return response

            return send_file(output_path, as_attachment=True, download_name='miitok_video.mp4')

    except yt_dlp.utils.DownloadError as e:
        return jsonify({'error': 'Download gagal: ' + str(e)[:150]}), 500
    except Exception as e:
        return jsonify({'error': str(e)[:200]}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
