from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import time
import threading
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# In-memory store for file metadata: {filename: {"token": str, "created_at": timestamp}}
FILE_METADATA = {}

# Cleanup thread to delete files older than 1 hour
def cleanup_old_files():
    while True:
        current_time = time.time()
        for filename, metadata in list(FILE_METADATA.items()):
            if current_time - metadata["created_at"] > 3600:  # 1 hour in seconds
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
                del FILE_METADATA[filename]
        time.sleep(300)  # Check every minute

# Start cleanup thread
threading.Thread(target=cleanup_old_files, daemon=True).start()

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')
    cookies = data.get('cookies')  # Optional cookies string
    formats = data.get('formats', ['best'])  # Default to 'best'

    if not video_url:
        return jsonify({
            "status": "error",
            "message": "URL is required",
            "error_code": "MISSING_URL"
        }), 400

    if not isinstance(formats, list):
        return jsonify({
            "status": "error",
            "message": "Formats must be a list",
            "error_code": "INVALID_FORMATS"
        }), 400

    try:
        base_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s-%(format_id)s.%(ext)s',
        }
        if cookies:
            temp_cookies_file = 'temp_cookies.txt'
            with open(temp_cookies_file, 'w') as f:
                f.write(cookies)
            base_opts['cookiefile'] = temp_cookies_file

        downloaded_files = []
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            for fmt in formats:
                ydl_opts = base_opts.copy()
                ydl_opts['format'] = fmt
                ydl.download([video_url])
                file_path = ydl.prepare_filename(info).replace('.%(ext)s', f'-{fmt.split("+")[0]}.{info.get("ext", "mp4")}')
                file_name = os.path.basename(file_path)
                
                # Generate a unique token for this file
                token = str(uuid.uuid4())
                FILE_METADATA[file_name] = {
                    "token": token,
                    "created_at": time.time()
                }
                
                # Construct URL with token (valid for 30 min)
                video_url = f"{request.host_url}downloads/{file_name}?token={token}"
                
                downloaded_files.append({
                    "file_path": file_path,
                    "video_url": video_url,
                    "format": fmt,
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', None),
                    "ext": info.get('ext', 'mp4')
                })

        if cookies and os.path.exists(temp_cookies_file):
            os.remove(temp_cookies_file)

        return jsonify({
            "status": "success",
            "message": "Videos downloaded successfully",
            "data": downloaded_files
        }), 200

    except Exception as e:
        if cookies and os.path.exists('temp_cookies.txt'):
            os.remove('temp_cookies.txt')
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_code": "DOWNLOAD_FAILED"
        }), 500

@app.route('/downloads/<filename>', methods=['GET'])
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    token = request.args.get('token')

    if not os.path.exists(file_path):
        return jsonify({
            "status": "error",
            "message": "File not found",
            "error_code": "FILE_NOT_FOUND"
        }), 404

    # Check if file metadata exists and token is valid
    if filename not in FILE_METADATA:
        return jsonify({
            "status": "error",
            "message": "File expired or invalid",
            "error_code": "FILE_EXPIRED"
        }), 410  # Gone

    metadata = FILE_METADATA[filename]
    if token != metadata["token"] or (time.time() - metadata["created_at"] > 1800):  # 30 min in seconds
        return jsonify({
            "status": "error",
            "message": "URL expired or invalid token",
            "error_code": "URL_EXPIRED"
        }), 403

    return send_file(file_path, as_attachment=True)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)