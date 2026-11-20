import io
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from .extensions import db
from .models import Attachment

MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_TOTAL_SIZE = 20 * 1024 * 1024
MAX_FILES_PER_RECORD = 5

ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
}


def _read_and_validate(upload):
    original_name = (upload.filename or "").replace("\\", "/").split("/")[-1]
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise ValueError(f"O arquivo '{original_name}' possui formato não permitido.")

    data = upload.stream.read(MAX_FILE_SIZE + 1)
    if not data:
        raise ValueError(f"O arquivo '{original_name}' está vazio.")
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"O arquivo '{original_name}' ultrapassa o limite de 8 MB.")

    mimetype = ALLOWED_TYPES[extension]
    if extension in {".png", ".jpg", ".jpeg", ".webp"}:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
                formats = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
                if image.format not in formats or formats[image.format] != (".jpg" if extension == ".jpeg" else extension):
                    raise ValueError(f"O conteúdo do arquivo '{original_name}' não corresponde à extensão.")
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            raise ValueError(f"A imagem '{original_name}' é inválida ou está corrompida.")
    elif extension == ".pdf" and not data.startswith(b"%PDF-"):
        raise ValueError(f"O arquivo '{original_name}' não parece ser um PDF válido.")
    elif extension in {".docx", ".xlsx", ".pptx"} and not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError(f"O documento '{original_name}' não parece ser um arquivo Office válido.")
    elif extension in {".doc", ".xls", ".ppt"} and not data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise ValueError(f"O documento '{original_name}' não parece ser um arquivo Office válido.")
    elif extension in {".txt", ".csv"} and b"\x00" in data:
        raise ValueError(f"O arquivo '{original_name}' contém dados não permitidos.")

    safe_name = secure_filename(original_name) or f"anexo{extension}"
    safe_name = safe_name[:240]
    return safe_name, mimetype, data


def save_uploaded_attachments(parent, parent_type, uploads, remove_ids=None):
    """Adiciona/remover anexos de um registro e deixa o commit para a rota."""
    relation_name = {
        "event": "event_id",
        "schedule_item": "schedule_item_id",
        "notice": "notice_id",
    }.get(parent_type)
    if not relation_name:
        raise ValueError("Tipo de registro inválido para anexos.")

    remove_ids = {int(value) for value in (remove_ids or []) if str(value).isdigit()}
    for attachment in list(parent.attachments):
        if attachment.id in remove_ids:
            parent.attachments.remove(attachment)

    selected_uploads = [upload for upload in uploads if upload and upload.filename]
    if len(parent.attachments) + len(selected_uploads) > MAX_FILES_PER_RECORD:
        raise ValueError(f"Cada publicação pode ter no máximo {MAX_FILES_PER_RECORD} anexos.")

    current_size = sum(item.file_size for item in parent.attachments)
    for upload in selected_uploads:
        filename, mimetype, data = _read_and_validate(upload)
        current_size += len(data)
        if current_size > MAX_TOTAL_SIZE:
            raise ValueError("O tamanho total dos anexos deste registro não pode ultrapassar 20 MB.")
        attachment = Attachment(
            original_filename=filename,
            mimetype=mimetype,
            file_size=len(data),
            data=data,
        )
        setattr(attachment, parent_type, parent)
        db.session.add(attachment)
