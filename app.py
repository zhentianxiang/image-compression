#!/usr/bin/env python3
"""Flask application for image compression."""

import os
import uuid
import zipfile
import io
import mimetypes
from flask import Flask, request, jsonify, send_file, render_template
from compress import compress_image, get_image_info, output_extension

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['COMPRESSED_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads', 'compressed')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRESSED_FOLDER'], exist_ok=True)

# In-memory file storage for simplicity
file_storage = {}  # file_id -> {'original': bytes, 'compressed': bytes, 'filename': str}


def download_filename(filename, output_format=None):
    """Keep the uploaded (source) base name for the downloaded file.

    The extension follows the real content: a PNG without transparency is
    re-encoded as JPEG, so the name must end with .jpg instead of .png.
    """
    if not output_format:
        return filename
    stem = os.path.splitext(filename)[0]
    return f"{stem}.{output_extension(output_format)}"


def image_mimetype(filename, output_format=None):
    """Guess the mimetype from the download name, falling back to the format."""
    guessed = mimetypes.guess_type(filename)[0]
    if guessed:
        return guessed
    return f"image/{output_extension(output_format)}"


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
        compressed, output_format = compress_image(
            io.BytesIO(original),
            quality=quality,
            original_format=file_ext
        )

        # Store compressed result
        file_storage[file_id]['compressed'] = compressed
        file_storage[file_id]['format'] = output_format
        file_storage[file_id]['compressed_name'] = download_filename(
            file_data['filename'], output_format
        )
        compressed_size = len(compressed)

        results.append({
            'id': file_id,
            'filename': file_data['filename'],
            'download_name': file_storage[file_id]['compressed_name'],
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': round((1 - compressed_size / original_size) * 100, 1) if original_size > 0 else 0
        })

    return jsonify({'success': True, 'files': results})


@app.route('/api/download/<file_id>')
def download_single(file_id):
    """Download a single compressed file, keeping the source file name."""
    if file_id not in file_storage:
        return jsonify({'error': 'File not found'}), 404

    file_data = file_storage[file_id]
    if file_data.get('compressed') is None:
        return jsonify({'error': 'File not compressed yet'}), 400

    compressed = file_data['compressed']
    output_format = file_data.get('format')
    filename = file_data.get('compressed_name') or download_filename(
        file_data['filename'], output_format
    )

    return send_file(
        io.BytesIO(compressed),
        mimetype=image_mimetype(filename, output_format),
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/download-all')
def download_all():
    """Download every compressed file as a ZIP, keeping the source file names."""
    compressed_only = [
        (file_id, file_data)
        for file_id, file_data in file_storage.items()
        if file_data.get('compressed') is not None
    ]

    if not compressed_only:
        return jsonify({'error': 'No compressed files'}), 400

    memory_file = io.BytesIO()
    used_names = set()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_id, file_data in compressed_only:
            compressed = file_data['compressed']
            # Same (source) file name as the single-file download; only the
            # extension follows the re-encoded format.
            name = file_data.get('compressed_name') or download_filename(
                file_data['filename'], file_data.get('format')
            )

            # Two uploads can share a name: keep ZIP entries unique.
            base, ext = os.path.splitext(name)
            candidate = name
            counter = 2
            while candidate.lower() in used_names:
                candidate = f"{base} ({counter}){ext}"
                counter += 1
            used_names.add(candidate.lower())

            zf.writestr(candidate, compressed)

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


@app.route('/api/remove/<file_id>', methods=['POST', 'DELETE'])
def remove(file_id):
    """Remove a single uploaded file."""
    file_storage.pop(file_id, None)
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)