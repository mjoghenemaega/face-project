#attendance/utils.py
import base64
import io
import logging
import os
from PIL import Image, ImageFile
import imagehash
import numpy as np
import cv2

# Configure logging
logger = logging.getLogger(__name__)

# Allow truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Load face detection cascade
CASCADE_PATH = cv2.data.haarcascades
FACE_CASCADE = cv2.CascadeClassifier(os.path.join(CASCADE_PATH, 'haarcascade_frontalface_default.xml'))

def base64_to_pil(b64_string):
    """Convert base64 string to PIL Image with enhanced error handling"""
    try:
        # Handle data URLs
        if b64_string.startswith("data:image"):
            b64_string = b64_string.split(",", 1)[1]

        # Clean up the string
        b64_string = b64_string.strip().replace("\n", "").replace("\r", "")

        # Add padding if needed
        padding = len(b64_string) % 4
        if padding:
            b64_string += "=" * (4 - padding)

        # Decode and convert to PIL
        image_data = base64.b64decode(b64_string)
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
        image.load()  # Force load image data
        return image

    except Exception as e:
        logger.error(f"Base64 decode error: {str(e)}")
        raise ValueError("Invalid image data")

def detect_and_crop_face(image, min_size_ratio=0.1):
    """Enhanced face detection with quality controls"""
    try:
        # Convert to OpenCV format if needed
        if isinstance(image, Image.Image):
            image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Convert to grayscale for detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect faces with optimized parameters
        faces = FACE_CASCADE.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        if len(faces) == 0:
            logger.warning("No face detected in image")
            return None

        # Get largest face
        if len(faces) > 1:
            faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
            logger.info(f"Multiple faces detected, using largest face")

        x, y, w, h = faces[0]

        # Add padding (15% on each side)
        pad_w = int(w * 0.15)
        pad_h = int(h * 0.15)
        x1 = max(0, x - pad_w)
        y1 = max(0, y - pad_h)
        x2 = min(image.shape[1], x + w + pad_w)
        y2 = min(image.shape[0], y + h + pad_h)

        # Crop and standardize size
        face = image[y1:y2, x1:x2]
        face = cv2.resize(face, (160, 160))

        # Check minimum face size ratio
        face_size_ratio = (x2 - x1) * (y2 - y1) / (image.shape[0] * image.shape[1])
        if face_size_ratio < min_size_ratio:
            logger.warning("Face too small in image")
            return None

        return Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))

    except Exception as e:
        logger.error(f"Face detection error: {str(e)}")
        return None

def check_face_quality(image):
    """Comprehensive face quality assessment"""
    if isinstance(image, Image.Image):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Brightness score
    brightness = np.mean(gray)
    brightness_score = 1.0 - abs(128 - brightness) / 128

    # Blur detection
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = min(1.0, np.var(laplacian) / 500)

    # Contrast score
    contrast = gray.std()
    contrast_score = min(contrast / 50.0, 1.0)

    # Weighted final score
    quality_score = (
        brightness_score * 0.3 +
        blur_score * 0.5 +
        contrast_score * 0.2
    )

    return quality_score

def compute_phash(image, hash_size=8):
    """Compute perceptual hash with standardized input"""
    if isinstance(image, np.ndarray):
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    return str(imagehash.average_hash(image, hash_size))

def phash_to_hex(phash):
    """Convert hash to hex string"""
    return str(phash)

def compare_phash(hash1, hash2):
    """Enhanced perceptual hash comparison"""
    try:
        if not hash1 or not hash2:
            return 0.0

        # Convert strings to integers
        hash1_int = int(hash1, 16)
        hash2_int = int(hash2, 16)

        # Calculate Hamming distance
        xor_result = bin(hash1_int ^ hash2_int).count('1')
        max_bits = len(hash1) * 4

        # Convert to similarity percentage with bounds checking
        similarity = ((max_bits - xor_result) / max_bits) * 100
        return max(0.0, min(100.0, similarity))

    except Exception as e:
        logger.error(f"Hash comparison error: {str(e)}")
        return 0.0



def verify_liveness(image):
    """Simplified liveness detection with basic checks"""
    if isinstance(image, Image.Image):
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Simplified checks
    # 1. Basic texture check
    texture_score = np.std(gray) / 128.0
    
    # 2. Basic edge check
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.count_nonzero(edges) / (edges.shape[0] * edges.shape[1])
    
    # More lenient scoring
    liveness_score = (edge_density * 0.3 + texture_score * 0.7)
    
    # Normalize score to be more permissive
    normalized_score = min(1.0, liveness_score * 1.5)  # Boost score by 50%
    
    return normalized_score