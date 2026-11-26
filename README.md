# 个人知识库与全文检索系统

Vue 3 + FastAPI + MySQL 实现的知识库应用。核心是一套自己实现的检索内核：
中文分词 → 倒排索引 → BM25 排序 → 关键词高亮，外加标签体系与相似笔记推荐。

> Python 期末项目 / 选题方向：Web 应用类（技术深度路线）
>
> 📘 想从零重建这个项目？看 [开发教程_从零实现.md](开发教程_从零实现.md)：
> 按阶段拆解每一步的实现原理、关键代码与验证方法。

---

## 一、功能一览

| 模块 | 功能 |
|---|---|
| 笔记管理 | 新增 / 编辑 / 删除 / 详情 / 分页列表 / 按标签过滤 |
| 全文检索 | 中文分词、BM25 相关度排序、命中片段高亮、分页 |
| 查询语法 | `+必含词`、`"完整短语"`、`#标签`，可组合使用 |
| 标签体系 | 标签自动去重、引用计数、标签云筛选 |
| 相似推荐 | 基于词条 Jaccard 相似度推荐相关笔记 |
| 双向链接 | 编辑正文时输入 `[[`，选择要引用的笔记。详情页显示本文引用和反向引用，目标改名后仍可跳转。 |
| 整库备份 | 在「导入与备份」下载或恢复 JSON，保留原始 ID、正文、标签、时间和回收站状态。相同记录跳过，ID 冲突时撤销整次恢复。 |
| 回收站 | 删除后隐藏笔记及其搜索结果，可在侧栏「回收站」恢复。 |
| 专题学习 | 从首页或搜索结果选笔记建专题，调整阅读顺序，标记未读、已读或待复习。可从专题目录或笔记末尾练习整个专题，也可只练该专题的错题。 |
| 自测复习 | 在笔记详情中选中原文制题。新题当天可练，错题次日再出现，也可立即打开错题回顾。连续记住后按 1、3、7、14、30 天安排复习。 |
| 基础自测 | 预置 50 道原创题，其中 15 道单选或数值题在提交后自动判分并显示解析，其余 35 道可对照参考答案自评。首次点击「开始基础自测」会补齐缺少的来源笔记。 |
| 学习进度备份 | 整库导出包含专题顺序、阅读位置、题目及复习日期，旧版笔记备份仍可恢复。 |
| 统计 | 笔记数、词条数、平均长度 |
| 安全 | 高亮先转义后插标签（防存储型 XSS）；前端再经 DOMPurify 净化 |

## 二、技术栈

**后端**：Python 3.13 / FastAPI / SQLAlchemy 2.0 / PyMySQL / Pydantic v2 / jieba / pytest
**数据库**：MySQL 8.0（utf8mb4）
**前端**：Vue 3 / Vite / Vue Router / Pinia / Element Plus / markdown-it / DOMPurify / highlight.js

## 三、目录结构

```
student/
├── fast_api/                 # 后端
│   ├── main.py               # ★ 程序入口
│   ├── app/
│   │   ├── config.py         # 配置（pydantic-settings 读 .env）
│   │   ├── db.py             # 引擎与会话
│   │   ├── models.py         # ORM：notes / tags / note_tags
│   │   ├── schemas.py        # 请求响应模型
│   │   ├── api/              # 路由：health / notes / search / tags
│   │   └── services/         # ★ 核心算法层（纯 Python，可单测）
│   │       ├── tokenizer.py      # 中文分词
│   │       ├── index_store.py    # 倒排索引 + 持久化
│   │       ├── ranker.py         # BM25 排序
│   │       ├── query_parser.py   # 查询语法解析
│   │       ├── highlight.py      # 高亮（防 XSS）
│   │       ├── recommend.py      # 相似推荐
│   │       └── index_manager.py  # 索引与数据库同步
│   ├── scripts/
│   │   ├── init_db.sql       # 建库建表建账号
│   │   └── seed_data.py      # 灌演示数据
│   ├── tests/                # ★ TDD 测试
│   └── requirements.txt
├── vue3/                     # 前端
│   └── src/{views,components,api,router}
└── venv/                     # 虚拟环境（不入库）
```

## 四、环境要求

- Python 3.11 及以上（开发验证于 3.13.7）
- Node.js 20 及以上
- MySQL 8.0（服务已启动，端口 3306）

## 五、快速开始

### 1. 建库建表

```bash
mysql -u root -p < fast_api/scripts/init_db.sql
```

会创建 `kb_db`（开发库）、`kb_test`（测试库）和账号 `kb_user`（默认密码 `change_me`，请自行修改）。

### 2. 安装后端依赖

```bash
python -m venv venv
venv/Scripts/pip.exe install -r fast_api/requirements.txt
```

### 3. 配置

复制 `fast_api/.env.example` 为 `fast_api/.env`，填入真实密码：

```ini
DATABASE_URL=mysql+pymysql://kb_user:你的密码@127.0.0.1:3306/kb_db?charset=utf8mb4
TEST_DATABASE_URL=mysql+pymysql://kb_user:你的密码@127.0.0.1:3306/kb_test?charset=utf8mb4
```

### 4. 灌演示数据（可选）

```bash
cd fast_api
../venv/Scripts/python.exe scripts/seed_data.py
```

### 5. 运行测试

```bash
cd fast_api
../venv/Scripts/python.exe -m pytest -q
```

测试库可用时，所有测试均应通过。
索引内核测试不需要数据库；接口测试需要 MySQL，连不上会自动跳过。

### 6. 启动

**开发模式（前后端分离）**

```bash
# 终端 1：后端
cd fast_api && ../venv/Scripts/python.exe main.py

# 终端 2：前端
cd vue3 && npm install && npm run dev
# 打开 http://localhost:5173
```

**演示模式（单进程，推荐答辩时用）**

```bash
cd vue3 && npm run build
cd ../fast_api && ../venv/Scripts/python.exe main.py
# 打开 http://127.0.0.1:8000
```

前端构建产物由 FastAPI 托管，`python main.py` 一条命令即可跑起完整应用。

### 7. 部署到服务器

> 📦 **手机访问 / 多人共用**：直接照 [deploy/DEPLOY.md](deploy/DEPLOY.md) 走，
> 里面有 Nginx 配置、systemd 服务、Basic Auth 账号、HTTPS 证书的完整步骤（约 10 分钟），
> 以及安全检查清单和排错表。`deploy/` 下已放好可直接复制的 `nginx-kb.conf` 和 `kb.service`。

> ⚠️ **部署前必读：本项目没有登录鉴权**，接口对访问者完全开放。
> 一旦挂到公网，任何人都能读完你的全部笔记（`GET /api/backup`），
> 也能删除笔记、恢复备份覆盖数据。**请务必按下面的"安全"一节处理。**

**步骤（以 Linux 服务器为例）**

```bash
# 1. 拉代码
git clone <你的仓库> && cd <仓库>/student

# 2. 后端依赖
python3 -m venv venv
./venv/bin/pip install -r fast_api/requirements.txt

# 3. 建库（事先装好 MySQL 8 并启动）
mysql -u root -p < fast_api/scripts/init_db.sql

# 4. 配置
cp fast_api/.env.example fast_api/.env
vi fast_api/.env
#   把 DATABASE_URL 的密码改成真实密码
#   把 HOST 改成 127.0.0.1（推荐，由 Nginx 反代）或 0.0.0.0

# 5. 构建前端（服务器需要 Node 20+）
cd vue3 && npm ci && npm run build && cd ..
#    服务器上没有 Node 的话：在本地 build 后把 vue3/dist 整个目录传上去

# 6. 灌演示数据（可选）
cd fast_api && ../venv/bin/python scripts/seed_data.py && cd ..

# 7. 启动
cd fast_api && ../venv/bin/python main.py
```

**用 systemd 常驻**

```ini
# /etc/systemd/system/kb.service
[Unit]
Description=Personal KB
After=network.target mysql.service

[Service]
User=www-data
WorkingDirectory=/srv/kb/student/fast_api
ExecStart=/srv/kb/student/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now kb
```

**没有 MySQL 的服务器：改用 SQLite**

代码已支持，改 `.env` 两行即可（相对路径按 `fast_api` 目录解析，与启动目录无关）：

```ini
DATABASE_URL=sqlite:///./kb.db
TEST_DATABASE_URL=sqlite:///./kb_test.db
```

启动时会自动建表（`Base.metadata.create_all`），**不需要跑 `init_db.sql`**。

| 要点 | 说明 |
|---|---|
| 数据文件 | `fast_api/kb.db`，备份就是拷这个文件（或用 `GET /api/backup` 导 JSON） |
| WAL 附属文件 | 运行时还会生成 `kb.db-wal` / `kb.db-shm`，拷贝备份时一并带走，或先停服务 |
| 并发 | SQLite 是单写者，写操作串行；个人使用够用，多人高并发不建议 |
| 外键 | 代码已开 `PRAGMA foreign_keys=ON`，否则 `ON DELETE CASCADE` 不会生效 |
| 事务 | 已关闭 pysqlite 的隐式 BEGIN 改由显式 BEGIN，保证事务/保存点语义正确 |
| 从 MySQL 迁移 | `GET /api/backup` 导出 JSON → 改 `.env` → 重启 → `POST /api/backup/restore` 导入 |

已在 SQLite 上验证：136 个测试全部通过，建表、灌数据、检索、软删除、级联均正常。

**⚠️ `--workers` 必须为 1**

倒排索引是**进程内内存对象**，每个 worker 各有一份。开多个 worker 会出现
"A 进程新增了笔记，B 进程搜不到"的诡异现象。要提升并发，靠前面加缓存或换架构，
不要直接加 worker。

**安全（公网部署必做，二选一）**

1. **只绑内网 + Nginx 反代加 Basic Auth**（推荐，不改代码）

   ```nginx
   server {
       listen 80;
       server_name kb.example.com;
       auth_basic "restricted";
       auth_basic_user_file /etc/nginx/.htpasswd;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

   ```bash
   sudo apt install apache2-utils
   sudo htpasswd -c /etc/nginx/.htpasswd yourname
   ```

2. **给写接口加 Token 校验**（需要改代码，可参照 `settings.secret_key`）

**其他注意事项**

| 项目 | 说明 |
|---|---|
| `HOST` | 默认 `127.0.0.1`，只监听本机；要对公网直连才改 `0.0.0.0` |
| `RELOAD` | 生产必须 `0`。开着会 fork 进程，且索引会各存一份 |
| `/docs` | 公网环境建议关掉：`FastAPI(docs_url=None, openapi_url=None)` |
| 建表 | 启动时会 `create_all` 兜底，但它**不会改已有表的字段**。改过模型要在服务器上手动 `ALTER` 或重建库 |
| 备份 | `GET /api/backup` 导出 JSON，`POST /api/backup/restore` 恢复 |
| 数据体积 | 索引文件在 `fast_api/data/index.json`，随笔记量增长，注意磁盘 |

## 六、接口一览

启动后访问 `/docs` 可交互调试。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查（含数据库连通性） |
| GET | `/api/notes` | 列表（`page` / `size` / `tag`） |
| POST | `/api/notes` | 新建 |
| GET | `/api/notes/{id}` | 详情 |
| PUT | `/api/notes/{id}` | 更新 |
| DELETE | `/api/notes/{id}` | 移入回收站 |
| GET | `/api/notes/trash` | 查看回收站 |
| POST | `/api/notes/{id}/restore` | 恢复笔记 |
| GET | `/api/notes/suggestions?q=关键词` | 按标题查找引用目标 |
| GET | `/api/notes/{id}/links` | 查看引用和反向引用 |
| GET | `/api/backup` | 下载整库备份 |
| POST | `/api/backup/restore` | 恢复整库备份 |
| GET | `/api/search` | 检索（支持 `+词` `"短语"` `#标签`） |
| GET | `/api/notes/{id}/related` | 相似笔记 |
| GET | `/api/tags` | 标签及计数 |
| GET | `/api/stats` | 统计信息 |

## 七、设计要点

1. **检索内核与 HTTP 解耦**：`services/` 全是纯函数或纯类，不依赖数据库和框架，
   因此可以用 pytest 直接驱动，TDD 才做得下去。
2. **索引与数据库双写一致性**：先提交数据库事务，成功后再更新内存索引；
   启动时若有数据库则全量重建索引，保证两边不会长期偏离。
3. **高亮先转义再插标签**：避免笔记正文里的 `<script>` 被当作 HTML 执行；
   前端渲染前再用 DOMPurify 过一遍（纵深防御）。
4. **同步路由写 `def`**：同步 SQLAlchemy 在 `async def` 中会阻塞事件循环，
   写成普通 `def` 会由 FastAPI 自动交给线程池。
5. **配置驱动**：`DATABASE_URL` 可整体替换，必要时切 SQLite 也能跑，代码零改动。

## 八、常见问题

| 现象 | 原因与处理 |
|---|---|
| `RuntimeError: 'cryptography' package is required` | MySQL 8 默认 `caching_sha2_password`，需装 `cryptography` |
| `Access denied for user 'kb_user'@'localhost'` | MySQL 里 `@'localhost'` 与 `@'127.0.0.1'` 是两个账号，按实际连接方式创建 |
| 中文变问号 | 建库、建表、连接串三处都要 `utf8mb4` |
| `Lost connection to MySQL server` | 连接池需 `pool_pre_ping=True` + `pool_recycle=3600` |
| 前端刷新 404 | 需由 FastAPI 托管 `dist` 并提供 SPA 回退（本项目已实现） |

## 九、测试驱动开发

核心功能（检索内核）按 Red → Green → Refactor 完成：

```
test: 添加索引内核与分词测试用例（Red —— 实现前先失败）
feat: 实现分词、倒排索引、BM25 排序…（Green —— 66 项测试全部通过）
refactor: 持久化用例改用项目内固定目录（Refactor）
```

覆盖率情况：`pytest --cov=app.services` 可查看（需安装 pytest-cov）。
