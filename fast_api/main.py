"""程序入口。

启动方式（在 fast_api 目录下）：

    python main.py

开发期前端单独跑：cd ../vue3 && npm run dev
生产/演示：npm run build 之后，FastAPI 会直接托管 vue3/dist。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import jieba
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.api import backup, health, imports, notes, search, study, tags
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Note, Tag
from app.services.index_manager import index_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("kb")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR.parent / "vue3" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时重建索引，退出时落盘。

    优先从数据库重建，保证索引与数据一致；数据库不可用时退回磁盘索引，
    这样即使 MySQL 没起来，检索功能依然能演示。
    """
    index_manager.load()
    try:
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            tag_names = [tag.name for tag in db.scalars(select(Tag)).all()]
            rows = db.scalars(select(Note).where(Note.active())).all()

        # 把已有标签名加进 jieba 词典：否则「后端」会被切成「后」「端」，
        # 标签检索命中率会明显下降
        for name in tag_names:
            if name:
                jieba.add_word(name)

        index_manager.rebuild([(n.id, n.full_text) for n in rows])
        logger.info("索引已从数据库重建：%d 篇笔记，%d 个词条", len(rows), len(index_manager.index.terms()))
    except Exception as exc:  # noqa: BLE001
        logger.warning("数据库不可用，改用磁盘索引（%s）", type(exc).__name__)
    yield
    index_manager.save()
    logger.info("索引已保存到 %s", settings.index_path)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)#中间件解决跨域

app.include_router(health.router)
app.include_router(backup.router)
app.include_router(study.router)
app.include_router(notes.router)
app.include_router(imports.router)
app.include_router(search.router)
app.include_router(tags.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """统一错误结构：{code, message}。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常: %s", request.url.path)
    return JSONResponse(status_code=500, content={"code": 500, "message": "服务器内部错误"})


# ---------- 前端托管（SPA） ----------
# index.html 必须禁缓存，否则前端重新构建后浏览器还拿旧 HTML，
# 会去请求已被删除的旧 bundle，出现"改了页面没变化"的假象。
_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}

if FRONTEND_DIST.is_dir():
    _assets = FRONTEND_DIST / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        """前端路由刷新不 404：找不到实体文件就回退到 index.html。"""
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="接口不存在")
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate, headers=_NO_CACHE)
        return FileResponse(FRONTEND_DIST / "index.html", headers=_NO_CACHE)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
