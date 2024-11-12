# backend/app.py

from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid
import re
import time
import threading
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

# Configurazione del logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)

DOWNLOADS_DIR = os.path.join(os.getcwd(), 'downloads')

if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# Configurazione del Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10 per minute"]
)
limiter.init_app(app)

# Regex per validare gli URL di YouTube
YOUTUBE_URL_REGEX = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
)

# Percorso del file dei cookie
COOKIES_FILE = os.path.join(os.getcwd(), 'cookies.txt')

# Percorso di FFmpeg
FFMPEG_PATH = os.path.join(os.getcwd(), 'ffmpeg.exe')

@app.route('/download', methods=['POST'])
@limiter.limit("5 per minute")  # Limite personalizzato per questo endpoint
def download_video():
    data = request.get_json()
    url = data.get('url')
    quality = data.get('quality', 'best')  # Valore di default 'best'
    
    if not url or not YOUTUBE_URL_REGEX.match(url):
        return jsonify({'error': 'URL non valido o mancante'}), 400

    video_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOADS_DIR, f'{video_id}.%(ext)s')

    # Mappa delle qualità disponibili
    quality_map = {
        'best': 'bestvideo+bestaudio/best',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best',
        '720p': 'bestvideo[height<=720]+bestaudio/best',
        '480p': 'bestvideo[height<=480]+bestaudio/best',
        '360p': 'bestvideo[height<=360]+bestaudio/best',
    }

    selected_quality = quality_map.get(quality, 'bestvideo+bestaudio/best')

    ydl_opts = {
        'format': selected_quality,
        'outtmpl': output_template,
        'noplaylist': True,
        'merge_output_format': 'mp4',
        'cookiefile': COOKIES_FILE,  # Utilizza i cookie per l'autenticazione
        'ffmpeg_location': FFMPEG_PATH,  # Specifica la posizione di FFmpeg
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Inizio del download per URL: {url} con qualità: {quality}")
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return jsonify({'download_id': video_id, 'filename': os.path.basename(filename)}), 200
    except Exception as e:
        logging.error(f"Errore durante il download: {e}")
        return jsonify({'error': f"Errore durante il download: {str(e)}"}), 500

@app.route('/download/<download_id>', methods=['GET'])
def get_download(download_id):
    # Cerca il file corrispondente al download_id
    for file in os.listdir(DOWNLOADS_DIR):
        if file.startswith(download_id):
            file_path = os.path.join(DOWNLOADS_DIR, file)
            return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File non trovato'}), 404

# Servire i file frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

# Pulizia dei file scaricati
CLEANUP_INTERVAL = 3600  # ogni ora
FILE_EXPIRATION = 86400  # 24 ore

def cleanup_downloads():
    current_time = time.time()
    for file in os.listdir(DOWNLOADS_DIR):
        file_path = os.path.join(DOWNLOADS_DIR, file)
        if os.path.isfile(file_path):
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > FILE_EXPIRATION:
                os.remove(file_path)
                logging.info(f'Rimosso: {file_path}')

def periodic_cleanup():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        cleanup_downloads()

cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(debug=True)
