from flask import Flask, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

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
            'quiet': True,  # Suppress console output
            'no_warnings': True,
            'format': 'all',  # Get all available formats
            'geturl': True,  # Extract URLs without downloading
            'simulate': True,  # Don’t download, just simulate
        }
        if cookies:
            temp_cookies_file = 'temp_cookies.txt'
            with open(temp_cookies_file, 'w') as f:
                f.write(cookies)
            ydl_opts['cookiefile'] = temp_cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            formats = info.get('formats', [])
            
            # Prepare response with direct URLs for each format
            available_formats = []
            for fmt in formats:
                format_id = fmt.get('format_id')
                url = fmt.get('url')
                if url:  # Only include formats with a direct URL
                    available_formats.append({
                        "format_id": format_id,
                        "url": url,
                        "ext": fmt.get('ext', 'mp4'),
                        "resolution": fmt.get('resolution', 'unknown'),
                        "size": fmt.get('filesize', None),  # May be None if not available
                        "vcodec": fmt.get('vcodec', 'none'),
                        "acodec": fmt.get('acodec', 'none')
                    })

        # Clean up temp cookies file if created
        if cookies and os.path.exists(temp_cookies_file):
            os.remove(temp_cookies_file)

        return jsonify({
            "status": "success",
            "message": "Format URLs extracted successfully",
            "data": {
                "title": info.get('title', 'Unknown'),
                "duration": info.get('duration', None),
                "formats": available_formats
            }
        }), 200

    except Exception as e:
        if cookies and os.path.exists('temp_cookies.txt'):
            os.remove('temp_cookies.txt')
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