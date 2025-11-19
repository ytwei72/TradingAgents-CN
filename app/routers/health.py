from fastapi import APIRouter
import time

router = APIRouter()

def get_version() -> str:
    return "0.1.0"

@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": get_version(),
        "timestamp": int(time.time())
    }
