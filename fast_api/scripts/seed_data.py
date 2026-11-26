"""灌演示数据（可重复执行：按标题去重，只补缺失的）。

用法（在 fast_api 目录下）：

    ..\\venv\\Scripts\\python.exe scripts\\seed_data.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.models import Note, Tag, TrashedNote  # noqa: E402
from app.services.index_manager import index_manager  # noqa: E402

NOTES = [
    # ---------- 检索 ----------
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
        "为什么搜 sql 搜不到 MySQL",
        "索引里存的是整词 mysql，sql 只是它的子串，精确匹配对不上。解决办法是两阶段检索："
        "精确失败后再按「包含关系」展开，sql 就能匹配到 mysql、postgresql、sqlite。",
        ["检索", "算法"],
    ),
    # ---------- 后端 ----------
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
        "N+1 查询问题",
        "查 10 篇笔记，每篇再单独查一次标签，就是 11 次查询。解决办法是用 selectinload 预加载关联数据，"
        "一次查完。SQLAlchemy 里 lazy=\"selectin\" 就是干这个的。",
        ["后端", "性能", "MySQL"],
    ),
    (
        "数据库连接池耗尽怎么排查",
        "先看 pool_size 和 max_overflow 是否够用，再看有没有忘记 close 的会话。"
        "常见根因是长事务：拿到连接后夹了慢查询或外部请求，连接被长期占用。",
        ["后端", "MySQL", "性能"],
    ),
    (
        "两阶段检索：精确优先，失败再模糊",
        "先做精确匹配，命中就返回；一条都没有才退化为「包含关系」匹配。"
        "好处是正常搜索的精度不受影响，只有输错或不完整时才放宽。全量模糊会把排序搞乱。",
        ["检索", "算法"],
    ),
    # ---------- 数据库 ----------
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
        "SQL 索引失效的常见场景",
        "列上做函数运算、隐式类型转换、前导模糊 like '%x'、以及不符合最左前缀原则，都会让索引失效。"
        "排查手段是看执行计划 EXPLAIN，关注 type 是不是 ALL。",
        ["MySQL", "性能", "数据库"],
    ),
    (
        "事务的 ACID 与隔离级别",
        "原子性、一致性、隔离性、持久性。隔离级别从低到高是读未提交、读已提交、可重复读、串行化，"
        "级别越高越安全但并发越差。MySQL 默认可重复读，靠 MVCC 减少锁竞争。",
        ["数据库", "MySQL"],
    ),
    (
        "为什么主键用自增整数",
        "自增整数插入时始终追加在 B+ 树最右侧，页分裂少；用随机 UUID 会导致随机写入，"
        "索引页频繁分裂，写入性能明显下降。",
        ["数据库", "性能"],
    ),
    # ---------- 数据结构与算法 ----------
    (
        "Python 字典的哈希表实现",
        "字典查找平均 O(1)，底层是开放寻址的哈希表。键必须可哈希，所以列表不能当键。"
        "3.7 之后字典保持插入顺序，这一点可以直接拿来当有序集合用。",
        ["数据结构", "Python"],
    ),
    (
        "列表与元组怎么选",
        "元组不可变、内存更省、可作字典键；列表可变、功能更全。语义上，元组表示「一条记录」，"
        "列表表示「一组同类元素」，按语义选比按性能选更好。",
        ["数据结构", "Python"],
    ),
    (
        "Jaccard 相似度做相关推荐",
        "把每篇笔记看成词条集合，两篇的交集除以并集就是相似度。它不需要向量和额外依赖，"
        "结果也好解释——重合的词越多越像。",
        ["算法", "推荐"],
    ),
    (
        "时间复杂度怎么估算",
        "关注循环的嵌套层数和每次操作的规模：顺序遍历是 O(n)，双层遍历是 O(n²)，"
        "二分查找 O(log n)。排序之后用双指针，经常能把 O(n²) 降到 O(n log n)。",
        ["算法", "数据结构"],
    ),
    # ---------- Python ----------
    (
        "用 dataclass 减少样板代码",
        "@dataclass 自动生成 __init__、__repr__、__eq__，字段带类型注解即可。"
        "加 frozen=True 就是不可变值对象，加 slots=True 还能省内存。",
        ["Python"],
    ),
    (
        "生成器与迭代器的区别",
        "生成器是用 yield 写出来的函数，属于迭代器的一种。它不一次性把所有元素算出来，"
        "处理大文件时内存占用是常数级，这是它相对列表最大的优势。",
        ["Python", "性能"],
    ),
    (
        "装饰器：把横切逻辑抽出来",
        "计时、重试、日志这类和业务无关的逻辑，用装饰器包一层最干净。"
        "关键是 functools.wraps 要保留原函数的 __name__ 和文档字符串，否则排查问题会很难受。",
        ["Python"],
    ),
    (
        "上下文管理器与 with 语句",
        "实现 __enter__ 和 __exit__ 就能用 with，保证资源一定被释放。"
        "文件、数据库连接、锁都该这样写。用 contextlib.contextmanager 可以把生成器变成上下文管理器。",
        ["Python"],
    ),
    (
        "异常处理：该捕获什么",
        "不要写裸的 except:，它会连 KeyboardInterrupt 一起吞掉。捕获具体异常类型，"
        "并且要么处理、要么加上下文后重新抛出，别悄悄吞掉。",
        ["Python", "健壮性"],
    ),
    (
        "类型注解的实际收益",
        "运行时不强制，但编辑器能补全、静态检查能提前发现错误。"
        "配合 Mapped[] 这类写法，代码本身就是文档，比注释更难过期。",
        ["Python"],
    ),
    (
        "Python 并发：线程、进程、协程怎么选",
        "IO 密集用线程或协程，CPU 密集用多进程。GIL 让线程无法并行执行 Python 字节码，"
        "但等待网络和磁盘时会释放 GIL，所以 IO 场景依然有效。",
        ["Python", "并发"],
    ),
    # ---------- 前端 ----------
    (
        "Vue 3 组合式 API 与选项式 API",
        "组合式 API 把同一功能的逻辑写在一起，选项式按 data、methods 分散。"
        "组件一大，组合式更好复用和阅读；小页面两者差别不大。",
        ["前端", "Vue"],
    ),
    (
        "Vite 为什么比 Webpack 快",
        "开发期利用浏览器原生 ESM，按需编译，不做全量打包；Webpack 要先构建完整依赖图。"
        "生产构建 Vite 用 Rollup，产物质量相当。",
        ["前端", "构建"],
    ),
    (
        "前端路由的两种模式",
        "history 模式地址干净，但服务端必须把未匹配路径回退到 index.html，否则刷新 404；"
        "hash 模式带 #，不需要服务端配合。本项目用 history 模式，并在 FastAPI 里做了回退。",
        ["前端", "Vue"],
    ),
    (
        "请求防抖与节流",
        "防抖是等用户停手再发一次（搜索框），节流是固定间隔最多发一次（滚动加载）。"
        "选错的典型症状：搜索框用节流，用户还在打字就一直在请求。",
        ["前端", "性能"],
    ),
    # ---------- 安全与测试 ----------
    (
        "存储型 XSS 的一个典型入口",
        "如果把用户输入直接拼进 innerHTML，笔记里写一段 img onerror 就能在别人浏览器执行脚本。"
        "正确做法是：先 HTML 转义，再插入高亮标签，前端渲染前再过一遍 DOMPurify。",
        ["安全", "前端"],
    ),
    (
        "测试驱动开发的红绿重构",
        "Red：先写测试并确认它失败，证明测试真的在测东西；Green：写最少的代码让它通过；"
        "Refactor：在测试保护下整理代码。三次提交就能完整留下证据链。",
        ["测试", "TDD"],
    ),
    (
        "单元测试与集成测试的边界",
        "单元测试只测一个函数，快、定位准；集成测试串起数据库和接口，能发现装配问题。"
        "检索内核属于前者，接口用例属于后者，本项目两层都有。",
        ["测试"],
    ),
    # ---------- 工程 ------------------------------------------------
    (
        "Git 提交信息的写法",
        "前缀用 feat、fix、refactor、test、docs，正文说清「做了什么、为什么」。"
        "写「update」等于什么都没说，半年后自己都看不懂。",
        ["工具", "工程"],
    ),
    (
        "日志分级与排查思路",
        "DEBUG 给开发、INFO 记关键流程、WARNING 是异常但可继续、ERROR 是需要人介入。"
        "排查时先看错误前后三行，比从头读日志高效得多。",
        ["工程", "健壮性"],
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
    TrashedNote.__table__.create(engine, checkfirst=True)
    added = 0
    skipped = 0
    with SessionLocal() as db:
        existing_titles = set(db.scalars(select(Note.title)).all())
        for title, content, tag_names in NOTES:
            if title in existing_titles:
                skipped += 1
                continue
            note = Note(title=title, content=content)
            note.tags = [get_or_create_tag(db, name) for name in tag_names]
            db.add(note)
            added += 1
        db.commit()

    with SessionLocal() as db:
        rows = db.scalars(select(Note).where(Note.active())).all()
        index_manager.rebuild([(note.id, note.full_text) for note in rows])

    index_manager.save()
    print(f"新增 {added} 篇，跳过已存在 {skipped} 篇")
    print(f"索引已重建：{index_manager.index.doc_count()} 篇文档，{len(index_manager.index.terms())} 个词条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
