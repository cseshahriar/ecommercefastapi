from slugify import slugify
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException
import shutil

UPLOAD_DIR = Path("media")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


async def save_upload_file(upload_file: UploadFile, sub_dir: str):
    if not upload_file or not upload_file.filename:
        return None

    ext = Path(upload_file.filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Invalid file type")

    filename = f"{uuid4().hex}{ext}"

    dir_path = UPLOAD_DIR / sub_dir
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    return str(file_path)


def generate_slug(name: str) -> str:
    return slugify(name)
