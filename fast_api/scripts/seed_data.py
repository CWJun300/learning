"""灌演示数据（幂等：库里已有笔记就跳过）。

用法（在 fast_api 目录下）：

    ..\\venv\\Scripts\\python.exe scripts\\seed_data.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Note, Tag  # noqa: E402
from app.services.index_manager import index_manager  # noqa: E402

NOTES = [
    (
        "倒排索引是什么",
        "倒排索引（Inverted Index）以词条为键、文档为值，把「文档 → 词」翻转成「词 → 文档」，"
        "这样搜索时不必逐篇扫描，直接拿到候选文档集合。它是全文检索的地基。",
        ["检索", "数据结构"],
    ),
    (
        "BM25 排序原理",
        "BM25 在 TF-IDF 基础上引入了两个参数：k1 控制词频饱和速度，b 控制文档长度归一化强度。"
        "词频涨到一定程度后分数不再线性增长，这是「饱和」；长文档天然词多，需要被惩罚，这是「归一化」。",
        ["检索", "算法"],
    ),
    (
        "jieba 中文分词实践",
        "jieba 支持自定义词典，用 load_userdict() 可以把专业词加进去，比如「倒排索引」「向量检索」，"
        "避免被切成两个词。对领域文本，这一步的效果提升非常明显。",
        ["检索", "NLP"],
    ),
    (
        "FastAPI 依赖注入",
        "用 Depends 声明依赖，框架负责实例化和回收。数据库会话就适合这样做：每个请求一个 Session，"
        "请求结束自动 close，不会泄漏连接。",
        ["FastAPI", "后端"],
    ),
    (
        "为什么同步路由要写 def",
        "FastAPI 里用 async def 却调用同步数据库驱动，会把事件循环堵死；写成普通 def，框架会自动丢到线程池执行，"
        "并发能力反而更好。这是最容易踩的坑之一。",
        ["FastAPI", "后端", "并发"],
    ),
    (
        "MySQL 连接池的三个关键参数",
        "pool_pre_ping 让取连接前先探活，pool_recycle 定期回收避免失效连接，pool_size 与 max_overflow 控制容量。"
        "MySQL 默认会断开空闲 8 小时的连接，不配这两项迟早遇到 Lost connection。",
        ["MySQL", "后端"],
    ),
    (
        "utf8mb4 为什么必须显式指定",
        "MySQL 建库、建表、连接串三处都要 utf8mb4，否则中文可能变问号，emoji 直接存不进去。"
        "utf8mb4_0900_ai_ci 是 MySQL 8 的默认排序规则，对中文比较友好。",
        ["MySQL"],
    ),
    (
        "存储型 XSS 的一个典型入口",
        "如果把用户输入直接拼进 innerHTML，笔记里写一段 img onerror 就能在别人浏览器执行脚本。"
        "正确做法是：先 HTML 转义，再插入高亮标签，前端渲染前再过一遍 DOMPurify。",
        ["安全", "前端"],
    ),
    (
        "Jaccard 相似度做相关推荐",
        "把每篇笔记看成词条集合，两篇的交集除以并集就是相似度。它不需要向量和额外依赖，"
        "结果也好解释——重合的词越多越像。",
        ["算法", "推荐"],
    ),
    (
        "测试驱动开发的红绿重构",
        "Red：先写测试并确认它失败，证明测试真的在测东西；Green：写最少的代码让它通过；"
        "Refactor：在测试保护下整理代码。三次提交就能完整留下证据链。",
        ["测试", "TDD"],
    ),
]


def get_or_create_tag(db, name: str) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.name == name))
    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()
    return tag


def main() -> int:
    with SessionLocal() as db:
        existing = db.scalar(select(func.count(Note.id))) or 0
        if existing:
            print(f"数据库已有 {existing} 篇笔记，跳过灌数据")
            return 0

        for title, content, tag_names in NOTES:
            note = Note(title=title, content=content)
            note.tags = [get_or_create_tag(db, name) for name in tag_names]
            db.add(note)
        db.commit()
        print(f"已写入 {len(NOTES)} 篇演示笔记")

    with SessionLocal() as db:
        rows = db.scalars(select(Note)).all()
        index_manager.rebuild([(note.id, note.full_text) for note in rows])
    index_manager.save()
    print(
        f"索引已重建：{index_manager.index.doc_count()} 篇文档，"
        f"{len(index_manager.index.terms())} 个词条"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
