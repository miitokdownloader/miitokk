from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL kosong'}), 400
    
    try:
        filename = f"{uuid.uuid4()}.mp4"
        output_path = f"/tmp/{filename}"
        
        ydl_opts = {
            'outtmpl': output_path,
            'format': 'best',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return send_file(output_path, as_attachment=True, download_name='miitok_video.mp4')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
