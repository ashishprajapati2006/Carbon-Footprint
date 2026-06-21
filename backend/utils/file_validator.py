import re
from typing import Set
from fastapi import HTTPException, status, UploadFile

def sanitize_filename(filename: str) -> str:
    """Sanitizes file name to prevent path traversal, hidden files, or weird characters."""
    import os
    # Get only base name
    base = os.path.basename(filename)
    # Remove any character that isn't alphanumeric, a dot, dash, or underscore
    base = re.sub(r'[^a-zA-Z0-9._-]', '', base)
    # Prevent leading dots/spaces
    base = base.lstrip('.')
    return base or "uploaded_file"

async def validate_uploaded_file(
    file: UploadFile,
    allowed_extensions: Set[str],
    allowed_mimes: Set[str],
    max_size: int
) -> bytes:
    """
    Validates an uploaded file.
    Checks:
    - Path traversal attempts or double extensions.
    - Matches extension and MIME types.
    - Restricts maximum file size.
    - Inspects file content magic bytes for PE binaries (MZ), ELF binaries (\x7fELF),
      or script shebangs (#!).
    - Validates PDF, PNG, and JPEG magic signatures to prevent spoofing.
    Returns:
      file_bytes (bytes)
    """
    filename = file.filename or ""
    
    # 1. Path traversal verification
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid directory path traversal characters."
        )

    sanitized = sanitize_filename(filename)
    
    # 2. Check for double extension execution patterns (e.g. image.png.exe)
    parts = sanitized.split('.')
    if len(parts) > 2:
        for part in parts[1:]:
            if part.lower() in ("exe", "sh", "bat", "cmd", "msi", "scr", "pif", "js", "vbs", "py", "bin"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Double extension or executable pattern detected in filename."
                )

    ext = sanitized.split('.')[-1].lower() if '.' in sanitized else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    # 3. MIME type validation
    mime = file.content_type or ""
    if mime.lower() not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type '{mime}'. Allowed: {', '.join(allowed_mimes)}"
        )

    # 4. Read file content and check size
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file upload stream: {e}"
        )

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {max_size / (1024 * 1024):.1f} MB."
        )

    # Reset upload file pointer just in case it's read again elsewhere
    file.file.seek(0)

    # 5. Inspect magic bytes for virus/executable safety
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

    # 6. Verify file signature against extension to prevent spoofing
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

    return content
