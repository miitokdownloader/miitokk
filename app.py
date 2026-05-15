from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request
import yt_dlp
import os
import uuid
import shutil

app = Flask(__name__, static_folder='static', static_url_path='/static')

@app.route('/static/makima.mp4')
def serve_video():
    video_path = os.path.join(app.static_folder, 'makima.mp4')
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
    # Support both form-data and JSON body
    if request.is_json:
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
        quality = data.get('quality', '').strip()
    else:
        url = (request.form.get('url') or '').strip()
        quality = (request.form.get('quality') or '').strip()

    print(f"[download] content-type={request.content_type!r} url={url!r} quality={quality!r}", flush=True)

    if not url:
        return jsonify({'error': 'Please paste TikTok URL'}), 400

    if not quality:
        return jsonify({'error': 'Please select quality'}), 400
    
    try:
        filename = f"{uuid.uuid4()}.mp4"
        output_path = f"/tmp/{filename}"
        
        if quality == 'audio':
            if shutil.which('ffmpeg') is None:
                return jsonify({'error': 'MP3 conversion requires FFmpeg installed on the server.'}), 400
            ydl_opts = {
                'outtmpl': output_path.replace('.mp4', '.mp3'),
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            audio_path = output_path.replace('.mp4', '.mp3')
            @after_this_request
            def cleanup_audio(response):
                try:
                    os.remove(audio_path)
                except OSError:
                    pass
                return response
            return send_file(
                audio_path,
                as_attachment=True,
                download_name='miitok_audio.mp3'
            )
        else:
            format_map = {
                'best': 'bestvideo+bestaudio/best',
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            }
            ydl_opts = {
                'outtmpl': output_path,
                'format': format_map.get(quality, 'best'),
                'merge_output_format': 'mp4',
                'noplaylist': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

            @after_this_request
            def cleanup_video(response):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
                return response

            # Cek kalau foto/slideshow
            if info.get('_type') == 'playlist':
                return jsonify({'error': 'Ini slideshow foto, belum support download foto TikTok'}), 400

            return send_file(
                output_path,
                as_attachment=True,
                download_name='miitok_video.mp4'
            )
    
    except yt_dlp.utils.DownloadError:
        return jsonify({'error': 'Download gagal. Cek link TikTok atau coba lagi.'}), 500
    except Exception as e:
        err_str = str(e)
        err_msg = err_str[:200] + ('...' if len(err_str) > 200 else '')
        return jsonify({'error': err_msg}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
