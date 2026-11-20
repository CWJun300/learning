# tools —— 离线依赖安装

## 为什么有这个目录

本机环境里 `pip install` 会失败（pip 的临时目录在下载后立刻变成不可访问，
报 `PermissionError: [WinError 5]`）。所以这里放了一个**不经过 pip 临时目录**的
安装脚本：直接下载 wheel → 解压进 `venv/Lib/site-packages`。

## 目录

```
tools/
├── install_offline.py     # 安装脚本
└── _wheels/               # 已下载好的依赖包（离线可复用，不进 git）
```

## 用法

在 `student` 目录下执行：

```powershell
# 装默认清单（pytest / sqlalchemy / pymysql / cryptography / jieba 等）
.\venv\Scripts\python.exe .\tools\install_offline.py

# 只装某几个
.\venv\Scripts\python.exe .\tools\install_offline.py requests rich
```

脚本会：

1. 到清华镜像查询该包的最新兼容版本（优先 `py3-none-any` / `cp313-win_amd64`）；
2. 下载到 `tools/_wheels/`（已有则跳过，天然支持离线重装）；
3. 解压到当前 Python 的 `site-packages`。

纯 Python 的源码包（如 `jieba` 只有 tar.gz）会单独处理：只取包目录，逐文件写出。

## 什么时候**不用**它

在能正常用 pip 的机器上（老师的环境通常可以），直接用标准方式：

```powershell
python -m venv venv
.\venv\Scripts\pip.exe install -r fast_api\requirements.txt
```

`requirements.txt` 才是给老师看的正规依赖清单，本目录只是本机环境的绕行方案。
