from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.index_manager import index_manager

router = APIRouter(prefix="/api", tags=["健康检查"])


@router.get("/health", summary="健康检查（含数据库连通性）")
def health(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001 - 健康检查要吞掉所有异常
        db_status = f"error: {type(exc).__name__}"

    return {
        "status": "ok",
        "db": db_status,
        "index_docs": index_manager.index.doc_count(),
    }
