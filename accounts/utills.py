# attendance/utils.py
import base64
from PIL import Image
import io

def base64_to_pil(b64_string):
    """
    Convert a base64 string (with or without data:image/... prefix) to a PIL Image.
    """
    try:
        # Handle both data URLs and plain base64
        if b64_string.startswith("data:image"):
            header, b64_data = b64_string.split(",", 1)
        else:
            b64_data = b64_string

        # Decode safely
        image_data = base64.b64decode(b64_data)
        return Image.open(io.BytesIO(image_data)).convert("RGB")

    except Exception as e:
        print("Base64 decode error:", e)
        raise ValueError("invalid image data")
