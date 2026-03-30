import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.routers.users import get_current_user   # require login
from app.models.user import User

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "resumes")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),   # must be logged in
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Use a UUID filename to avoid collisions and path-traversal risks
    filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    return {"resume_url": f"/uploads/resumes/{filename}"}
