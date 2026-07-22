from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_AVATAR_SIZE = 5 * 1024 * 1024


def avatar_upload_path(user, filename):
    extension = Path(filename).suffix.lower()
    return f'avatars/{user.pk}/{uuid4().hex}{extension}'


def validate_avatar(upload):
    extension = Path(upload.name).suffix.lower()
    if extension not in AVATAR_EXTENSIONS:
        raise ValidationError('Avatar must be a JPG, JPEG, PNG, or WebP image.')
    if upload.size > MAX_AVATAR_SIZE:
        raise ValidationError('Avatar size cannot exceed 5 MB.')
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError('Upload a valid image file.') from error
