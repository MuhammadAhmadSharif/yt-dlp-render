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
    formats = data.get('formats', ['best'])  # Default to 'best' if not specified

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
        # Base options for yt-dlp
        base_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s-%(format_id)s.%(ext)s',  # Include format_id in filename
        }
        if cookies:
            temp_cookies_file = 'temp_cookies.txt'
            with open(temp_cookies_file, 'w') as f:
                f.write(cookies)
            base_opts['cookiefile'] = temp_cookies_file

        # Download each format
        downloaded_files = []
        with yt_dlp.YoutubeDL(base_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)  # Get info without downloading yet
            for fmt in formats:
                ydl_opts = base_opts.copy()
                ydl_opts['format'] = fmt
                ydl.download([video_url])  # Download with specific format
                file_path = ydl.prepare_filename(info).replace('.%(ext)s', f'-{fmt.split("+")[0]}.{info.get("ext", "mp4")}')
                file_name = os.path.basename(file_path)
                video_url = f"{request.host_url}downloads/{file_name}"
                downloaded_files.append({
                    "file_path": file_path,
                    "video_url": video_url,
                    "format": fmt,
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', None),
                    "ext": info.get('ext', 'mp4')
                })

        # Clean up temp cookies file if it was created
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