"""Image compression utilities using Pillow."""

import io
from PIL import Image


def get_image_info(file_obj):
    """Get image information without saving to disk."""
    try:
        img = Image.open(file_obj)
        return {
            'width': img.width,
            'height': img.height,
            'format': img.format,
            'mode': img.mode
        }
    except Exception:
        return {}


def compress_image(file_obj, quality=80, original_format=None):
    """Compress an image and return compressed bytes."""
    img = Image.open(file_obj)

    # Parse extension from original_format (remove dot if present)
    ext = original_format or img.format or 'jpg'
    ext = ext.lstrip('.').upper()

    output_buffer = io.BytesIO()

    # For PNG with transparency, keep as PNG
    if ext == 'PNG':
        if img.mode == 'RGBA':
            img.save(output_buffer, format='PNG', optimize=True)
            return output_buffer.getvalue()
        else:
            # Convert to JPEG for better compression
            ext = 'JPEG'

    # Convert quality slider to actual JPEG quality
    # 80% slider -> quality 60, 50% slider -> quality 37, etc.
    actual_quality = int(quality * 0.75)
    actual_quality = max(15, min(95, actual_quality))

    save_kwargs = {
        'format': 'JPEG',
        'quality': actual_quality,
        'optimize': True,
        'progressive': True
    }

    # Apply subsampling for better compression at lower qualities
    if actual_quality < 50:
        save_kwargs['subsampling'] = 4  # 4:1:1 - best compression
    elif actual_quality < 70:
        save_kwargs['subsampling'] = 2  # 4:2:0

    img = img.convert('RGB')
    img.save(output_buffer, **save_kwargs)
    return output_buffer.getvalue()