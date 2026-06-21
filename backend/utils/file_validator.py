import re
from typing import Set
from fastapi import HTTPException, status, UploadFile

def sanitize_filename(filename: str) -> str:
    """Sanitizes file name to prevent path traversal, hidden files, or weird characters."""
    import os
    base = os.path.basename(filename)
    base = re.sub(r'[^a-zA-Z0-9._-]', '', base)
    base = base.lstrip('.')
    return base or "uploaded_file"

async def validate_uploaded_file(
    file: UploadFile,
    allowed_extensions: Set[str],
    allowed_mimes: Set[str],
    max_size: int
) -> bytes:
    """Validates an uploaded file: size, extensions, magic bytes, and signature verification."""
    filename = file.filename or ""
    _check_filename_traversal(filename)
    sanitized = sanitize_filename(filename)
    _check_double_extension(sanitized)

    ext = sanitized.split('.')[-1].lower() if '.' in sanitized else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    mime = file.content_type or ""
    if mime.lower() not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type '{mime}'. Allowed: {', '.join(allowed_mimes)}"
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read upload stream: {e}")

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds limit of {max_size / (1024 * 1024):.1f} MB."
        )

    file.file.seek(0)
    _check_magic_bytes(content)
    _check_spoofing_signature(content, ext)
    return content

def _check_filename_traversal(filename: str) -> None:
    """Ensures filename doesn't contain traversal markers."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid directory path traversal characters."
        )

def _check_double_extension(sanitized: str) -> None:
    """Blocks files with dangerous nested extension keywords."""
    parts = sanitized.split('.')
    if len(parts) > 2:
        for part in parts[1:]:
            if part.lower() in ("exe", "sh", "bat", "cmd", "msi", "scr", "pif", "js", "vbs", "py", "bin"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Double extension or executable pattern detected in filename."
                )

def _check_magic_bytes(content: bytes) -> None:
    """Performs virus and executable detection using binary headers."""
    if content.startswith(b'MZ'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malicious upload rejected: File header matches Windows executable (PE) binary."
        )
    if content.startswith(b'\x7fELF'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malicious upload rejected: File header matches Linux ELF binary."
        )
    if content.startswith(b'#!'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malicious upload rejected: File starts with a script shebang signature."
        )

def _check_spoofing_signature(content: bytes, ext: str) -> None:
    """Verifies image and document payloads against expected headers."""
    if ext == 'pdf' and not content.startswith(b'%PDF'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spoofing check failed: File extension is PDF, but PDF header signature is missing."
        )
    if ext == 'png' and not content.startswith(b'\x89PNG\r\n\x1a\n'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spoofing check failed: File extension is PNG, but PNG header signature is missing."
        )
    if ext in ('jpg', 'jpeg') and not content.startswith(b'\xff\xd8'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spoofing check failed: File extension is JPEG, but JPEG header signature is missing."
        )
