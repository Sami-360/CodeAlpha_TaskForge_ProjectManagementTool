import mimetypes
from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError

ATTACHMENT_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.webp', '.pdf', '.txt', '.doc', '.docx', '.xls',
    '.xlsx', '.zip',
}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024


def attachment_upload_path(attachment, filename):
    extension = Path(filename).suffix.lower()
    return f'task_attachments/{attachment.task_id}/{uuid4().hex}{extension}'


def validate_attachment(upload):
    extension = Path(upload.name).suffix.lower()
    if extension not in ATTACHMENT_EXTENSIONS:
        raise ValidationError('This attachment type is not supported.')
    if upload.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError('Attachment size cannot exceed 10 MB.')
    content_type = getattr(upload, 'content_type', None)
    expected_type, _ = mimetypes.guess_type(upload.name)
    if content_type and expected_type and content_type != expected_type:
        compatible = content_type == 'application/octet-stream'
        if not compatible:
            raise ValidationError('Attachment content type does not match its extension.')
