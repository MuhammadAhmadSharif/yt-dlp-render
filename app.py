from flask import Flask, request, jsonify
import yt_dlp
import json
import os
import logging
from io import StringIO

app = Flask(__name__)

# Configure logging with DEBUG level
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LogCapture(StringIO):
    """Captures yt-dlp output for logging."""
    def write(self, message):
        if message.strip():
            logger.debug(f"yt-dlp output: {message.strip()}")

def extract_format_info(format_data):
    """Extracts format info from yt-dlp data, matching the Flutter script."""
    return {
        "formatId": format_data.get("format_id", "unknown"),
        "ext": format_data.get("ext", "unknown"),
        "resolution": (
            format_data.get("resolution", "unknown")
            if format_data.get("vcodec", "none") != "none"
            else "audio only"
        ),
        "bitrate": int(format_data.get("tbr", 0) or 0),
        "size": int(
            format_data.get("filesize", 0) or format_data.get("filesize_approx", 0) or 0
        ),
        "vcodec": format_data.get("vcodec", "none"),
        "acodec": format_data.get("acodec", "none"),
        "url": format_data.get("url", None)  # Add direct URL for client-side download
    }

@app.route('/download', methods=['POST'])
def get_video_info():
    data = request.get_json()
    video_url = data.get('url')
    cookies = data.get('cookies')  # Optional cookies string

    if not video_url:
        return jsonify({
            "status": "error",
            "message": "URL is required",
            "error_code": "MISSING_URL"
        }), 400

    log_capture = LogCapture()
    ydl_opts = {
        "quiet": True,  # Suppress console output
        "no_warnings": True,
        "format": "all",  # Extract all formats
        "geturl": True,  # Get direct URLs without downloading
        "simulate": True,  # Don’t download, just extract info
        "logger": logger,
        "logtostderr": True,
        "errfile": log_capture,
        "outfile": log_capture
    }

    if cookies:
        temp_cookies_file = 'temp_cookies.txt'
        with open(temp_cookies_file, 'w') as f:
            f.write(cookies)
        ydl_opts['cookiefile'] = temp_cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video_info = {
                "title": info.get("title", "unknown_video"),
                "thumbnail": info.get("thumbnail"),
                "formats": [extract_format_info(f) for f in info.get("formats", [])],
            }
            logger.info(f"Fetched info for {video_url}: {len(video_info['formats'])} formats")

        # Clean up temp cookies file if created
        if cookies and os.path.exists(temp_cookies_file):
            os.remove(temp_cookies_file)

        return jsonify({
            "status": "success",
            "message": "Format URLs extracted successfully",
            "data": video_info
        }), 200

    except Exception as e:
        if cookies and os.path.exists('temp_cookies.txt'):
            os.remove('temp_cookies.txt')
        logger.error(f"Error fetching info for {video_url}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "error_code": "EXTRACTION_FAILED"
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)