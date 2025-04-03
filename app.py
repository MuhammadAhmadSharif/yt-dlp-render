from flask import Flask, request, jsonify, send_file
import yt_dlp
import os

app = Flask(__name__)

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')
    cookies = data.get('cookies')  # Optional cookies string

    if not video_url:
        return jsonify({
            "status": "error",
            "message": "URL is required",
            "error_code": "MISSING_URL"
        }), 400

    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'format': 'best',
        }
        if cookies:
            with open('temp_cookies.txt', 'w') as f:
                f.write(cookies)
            ydl_opts['cookiefile'] = 'temp_cookies.txt'  # Fixed: Removed extra ]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)

        if cookies and os.path.exists('temp_cookies.txt'):
            os.remove('temp_cookies.txt')  # Clean up

        # Construct a URL for the file
        file_name = os.path.basename(file_path)
        video_url = f"{request.host_url}downloads/{file_name}"

        return jsonify({
            "status": "success",
            "message": "Video downloaded successfully",
            "data": {
                "file_path": file_path,
                "video_url": video_url,
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', None),
                "format": info.get('ext', 'mp4')
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_code": "DOWNLOAD_FAILED"
        }), 500

@app.route('/downloads/<filename>', methods=['GET'])
def serve_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({
        "status": "error",
        "message": "File not found",
        "error_code": "FILE_NOT_FOUND"
    }), 404

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)