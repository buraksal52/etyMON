from fastapi import HTTPException


ALLOWED_UPLOAD_TYPES = {
    "image/jpeg": ("jpg", 10 * 1024 * 1024),
    "image/png": ("png", 10 * 1024 * 1024),
    "image/webp": ("webp", 10 * 1024 * 1024),
    "application/pdf": ("pdf", 15 * 1024 * 1024),
}


def validate_file_signature(content: bytes, content_type: str) -> None:
    signatures = {
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
        "application/pdf": content.startswith(b"%PDF"),
    }
    if not signatures.get(content_type, False):
        raise HTTPException(status_code=415, detail="File content does not match its MIME type")
