#!/usr/bin/env python3
"""Flask application for image compression."""

import os
import uuid
import zipfile
import io
from flask import Flask, request, jsonify, send_file, render_template
from compress import compress_image, get_image_info

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['COMPRESSED_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads', 'compressed')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

# In-memory file storage for simplicity
file_storage = {}  # file_id -> {'original': bytes, 'compressed': bytes, 'filename': str}


def cleanup_old_files():
    """Clean up files older than 1 hour."""
    import time
    current_time = time.time()
    to_delete = []
    for file_id, data in file_storage.items():
        if data.get('created_at', 0) < current_time - 3600:
            to_delete.append(file_id)
    for file_id in to_delete:
        del file_storage[file_id]


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    """Handle image upload."""
    cleanup_old_files()

    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'error': 'No files selected'}), 400

    results = []
    for f in files:
        if f.filename == '':
            continue

        # Check file extension
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
            continue

        file_id = str(uuid.uuid4())
        content = f.read()

        file_storage[file_id] = {
            'original': content,
            'compressed': None,
            'filename': f.filename,
            'created_at': __import__('time').time()
        }

        original_size = len(content)
        info = get_image_info(io.BytesIO(content))

        results.append({
            'id': file_id,
            'filename': f.filename,
            'original_size': original_size,
            'width': info.get('width'),
            'height': info.get('height'),
            'format': info.get('format')
        })

    return jsonify({'success': True, 'files': results})


@app.route('/api/compress', methods=['POST'])
def compress():
    """Compress images."""
    data = request.get_json()
    file_ids = data.get('file_ids', [])
    quality = data.get('quality', 80)

    results = []
    for file_id in file_ids:
        if file_id not in file_storage:
            continue

        file_data = file_storage[file_id]
        original = file_data['original']
        original_size = len(original)

        # Compress the image
        file_ext = os.path.splitext(file_data['filename'])[1].lower()
        compressed = compress_image(
            io.BytesIO(original),
            quality=quality,
            original_format=file_ext
        )

        # Store compressed result
        file_storage[file_id]['compressed'] = compressed
        compressed_size = len(compressed)

        results.append({
            'id': file_id,
            'filename': file_data['filename'],
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': round((1 - compressed_size / original_size) * 100, 1) if original_size > 0 else 0
        })

    return jsonify({'success': True, 'files': results})


@app.route('/api/download/<file_id>')
def download_single(file_id):
    """Download a single compressed file."""
    if file_id not in file_storage:
        return jsonify({'error': 'File not found'}), 404

    file_data = file_storage[file_id]
    compressed = file_data.get('compressed') or file_data['original']
    filename = file_data['filename']

    return send_file(
        io.BytesIO(compressed),
        mimetype='image/' + os.path.splitext(filename)[1][1:],
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/download-all')
def download_all():
    """Download all compressed files as ZIP."""
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_id, file_data in file_storage.items():
            compressed = file_data.get('compressed') or file_data['original']
            filename = file_data['filename']

            # Add compressed_ prefix to filename
            name, ext = os.path.splitext(filename)
            new_filename = f"compressed_{name}{ext}"

            zf.writestr(new_filename, compressed)

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='compressed_images.zip'
    )


@app.route('/api/clear', methods=['POST'])
def clear():
    """Clear all uploaded files."""
    file_storage.clear()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)