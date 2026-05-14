from flask import Flask, render_template, request, jsonify, send_file, Response
import yt_dlp
import os
import uuid

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
    url = request.json.get('url')
    quality = request.json.get('quality', 'best')
    
    if not url:
        return jsonify({'error': 'URL kosong'}), 400
    
    try:
        filename = f"{uuid.uuid4()}.mp4"
        output_path = f"/tmp/{filename}"
        
        if quality == 'audio':
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
            return send_file(
                output_path.replace('.mp4', '.mp3'),
                as_attachment=True,
                download_name='miitok_audio.mp3'
            )
        else:
            format_map = {
                'best': 'bestvideo+bestaudio/best',
                '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            }
            ydl_opts = {
                'outtmpl': output_path,
                'format': format_map.get(quality, 'best'),
                'merge_output_format': 'mp4',
                'noplaylist': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Cek kalau foto/slideshow
                if info.get('_type') == 'playlist':
                    return jsonify({'error': 'Ini slideshow foto, belum support download foto TikTok'}), 400
                    
            return send_file(
                output_path,
                as_attachment=True,
                download_name='miitok_video.mp4'
            )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
