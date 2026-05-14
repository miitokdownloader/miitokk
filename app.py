from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid
import requests

app = Flask(__name__, static_folder='static', static_url_path='/static')

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
