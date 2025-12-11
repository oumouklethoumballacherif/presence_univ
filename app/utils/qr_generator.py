import qrcode
from io import BytesIO
import base64
from datetime import datetime


def generate_qr_code(data, size=10):
    """
    Generate QR code image as base64 string.
    
    Args:
        data: The data to encode in the QR code
        size: Box size (default 10)
    
    Returns:
        Base64 encoded PNG image string
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#163A59", back_color="white")
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str


def generate_attendance_qr(course_id, token):
    """
    Generate attendance QR code with course info and token.
    
    Args:
        course_id: The course session ID
        token: The validation token
    
    Returns:
        Base64 encoded QR code image
    """
    # QR data format: course_id|token|timestamp
    timestamp = int(datetime.utcnow().timestamp())
    data = f"{course_id}|{token}|{timestamp}"
    
    return generate_qr_code(data, size=12)


def parse_qr_data(qr_data):
    """
    Parse QR code data.
    
    Args:
        qr_data: The scanned QR code data
    
    Returns:
        Tuple of (course_id, token, timestamp) or None if invalid
    """
    try:
        parts = qr_data.split('|')
        if len(parts) != 3:
            return None
        
        course_id = int(parts[0])
        token = parts[1]
        timestamp = int(parts[2])
        
        return course_id, token, timestamp
    except (ValueError, IndexError):
        return None
