from flask import Flask, request, jsonify, send_file
import yt_dlp
import os

app = Flask(__name__)

# Default download directory
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@app.route('/download', methods=['POST'])
def download_video():
    # Get URL from request body
    data = request.get_json()
    video_url = data.get('url')

    if not video_url:
        return jsonify({"error": "URL is required"}), 400

    try:
        # yt-dlp options
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',  # Save file with title
            'format': 'best',  # Download best quality
        }

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)

        # Return the file as a response
        return send_file(file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)