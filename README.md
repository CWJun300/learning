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
