# 部署指南：Nginx + Basic Auth + HTTPS（手机可访问）

目标：**用手机浏览器随时访问，几个人共用一个账号密码**，数据全程加密传输。

预计耗时 **10 分钟**（不含拉代码和装依赖）。

---

## 前置检查（先花 1 分钟确认）

| 检查项 | 怎么查 | 不满足怎么办 |
|---|---|---|
| 服务器有公网 IP | `curl -s ifconfig.me` | 内网机器需要端口转发或云厂商的隧道 |
| 有域名 | — | 没有也能做，走[自签证书](#路线-b没有域名自签证书) |
| 能装 nginx | `sudo apt install nginx` | — |
| 服务器在国内 | — | **域名未备案会被封 80/443**，见文末[国内服务器](#国内服务器的两个坑) |

---

## 步骤 0：把项目跑起来（3 分钟）

```bash
# 1. 拉代码
sudo mkdir -p /srv/kb && sudo chown $USER /srv/kb
git clone <你的仓库地址> /srv/kb
cd /srv/kb/student

# 2. 后端依赖
python3 -m venv venv
./venv/bin/pip install -r fast_api/requirements.txt

# 3. 配置（没有 MySQL 就用 SQLite，不用装任何东西）
cp fast_api/.env.example fast_api/.env
vi fast_api/.env
```

`.env` 里关键几行：

```ini
# 用 SQLite（推荐，零依赖）
DATABASE_URL=sqlite:///./kb.db
TEST_DATABASE_URL=sqlite:///./kb_test.db

# 只监听本机，由 Nginx 对外
HOST=127.0.0.1
PORT=8000
RELOAD=0
```

```bash
# 4. 构建前端（服务器要装 Node 20+）
cd vue3 && npm ci && npm run build && cd ..
#    没装 Node 的话：本地 build 完把 vue3/dist 整个目录 scp 上去

# 5. 试跑一下，确认能起来
cd fast_api
DATABASE_URL=sqlite:///./kb.db ../venv/bin/python main.py
# 浏览器/curl 访问 http://127.0.0.1:8000/api/health 应返回 ok
# Ctrl+C 停掉，交给 systemd 管
```

**可选**：灌演示数据

```bash
../venv/bin/python scripts/seed_data.py
```

---

## 步骤 1：systemd 常驻（2 分钟）

```bash
sudo cp /srv/kb/student/deploy/kb.service /etc/systemd/system/

# 路径不一样的话改这两行：
#   WorkingDirectory=/srv/kb/student/fast_api
#   ExecStart=/srv/kb/student/venv/bin/python ...

sudo systemctl daemon-reload
sudo systemctl enable --now kb
systemctl status kb --no-pager
```

看到 `Active: active (running)` 就好。

> ⚠️ `--workers` 必须保持 **1**。倒排索引是进程内内存对象，多 worker 会各存一份，
> 出现"A 进程新增了笔记，B 进程搜不到"。

看日志：

```bash
sudo journalctl -u kb -f
```

---

## 步骤 2：Nginx + 账号密码（3 分钟）

```bash
# 1. 装 nginx 和 htpasswd 工具
sudo apt update && sudo apt install -y nginx apache2-utils

# 2. 建账号（用户名 share，密码自己定）
sudo htpasswd -c /etc/nginx/.htpasswd share
# 回车后输两次密码

# 3. 放配置
sudo cp /srv/kb/student/deploy/nginx-kb.conf /etc/nginx/sites-available/kb.conf
sudo vi /etc/nginx/sites-available/kb.conf
#    把 kb.example.com 全部替换成你的域名（或服务器 IP）

sudo ln -s /etc/nginx/sites-available/kb.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default     # 去掉默认站点

# 4. 检查语法并重载
sudo nginx -t && sudo systemctl reload nginx
```

**给多人用怎么办？** 每个人一个账号，方便单独撤销：

```bash
sudo htpasswd /etc/nginx/.htpasswd alice    # 注意：不要加 -c，否则会覆盖整个文件
sudo htpasswd /etc/nginx/.htpasswd bob
sudo systemctl reload nginx

# 撤销某人
sudo htpasswd -D /etc/nginx/.htpasswd bob
sudo systemctl reload nginx
```

> 前端不用改。浏览器认证通过后会自动给同源请求带 `Authorization` 头。
> 用 curl 测试要手动加：`curl -u share:密码 https://你的域名/api/health`

---

## 步骤 3：配 HTTPS（2 分钟）

### 路线 A：有域名（推荐）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d kb.example.com
# 按提示填邮箱、同意条款，选"自动跳转 HTTPS"
```

certbot 会自动改写 nginx 配置里的证书路径，**`nginx-kb.conf` 里那两行 `ssl_certificate` 会被它覆盖**，所以不用手改。

续期是自动的，验证一下：

```bash
sudo certbot renew --dry-run
```

### 路线 B：没有域名（自签证书）

手机能访问，但**第一次会弹"不安全"警告**，点"继续访问"即可。数据依然是加密的。

```bash
sudo mkdir -p /etc/ssl/kb
sudo openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout /etc/ssl/kb/kb.key -out /etc/ssl/kb/kb.crt \
  -subj "/CN=kb" -addext "subjectAltName=IP:你的服务器公网IP"

sudo chmod 600 /etc/ssl/kb/kb.key
```

然后把 `nginx-kb.conf` 里的证书路径改掉，`server_name` 写成 IP：

```nginx
server_name 1.2.3.4;
ssl_certificate     /etc/ssl/kb/kb.crt;
ssl_certificate_key /etc/ssl/kb/kb.key;
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 步骤 4：手机验证（1 分钟）

1. 手机浏览器打开 `https://你的域名`
2. 弹出登录框 → 输入刚才 `htpasswd` 设的账号密码
3. 勾选"记住密码"
4. 浏览器菜单 → **添加到主屏幕**，以后像 App 一样点开

能正常新建/搜索笔记就成功了。

**注意**：用**系统浏览器**（Safari / Chrome）。微信、QQ 的内置浏览器有时不弹登录框，会一直白屏或 401。

---

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `502 Bad Gateway` | 后端没起来 | `systemctl status kb`、`journalctl -u kb -n 50` |
| 一直弹登录框（输对也弹） | htpasswd 路径错 / nginx 读不到文件 | `ls -l /etc/nginx/.htpasswd`，权限给 `644` |
| 电脑能开，手机打不开 | 云安全组没放行 443 | 控制台 → 安全组 → 入站规则加 443 |
| 手机浏览器提示证书无效 | 用了自签证书 | 正常现象，点"继续"；想消除就换成路线 A |
| 域名打不开、IP 能开 | DNS 没解析对 | `dig kb.example.com` 看解析是否指向服务器 |
| 白屏但接口正常 | `dist` 没构建 | `ls vue3/dist/index.html`，没有就 `npm run build` |
| 中文变方块 | 数据库编码 | SQLite 无此问题；MySQL 要 utf8mb4 |

### 国内服务器的两个坑

1. **域名未备案，80/443 会被阻断**。要么用非标准端口（`8443`，云安全组放行后访问 `https://域名:8443`），要么只用 IP + 自签证书。
2. 部分云厂商默认关闭 80/443 入站，要去控制台安全组手动加。

---

## 日常维护

```bash
# 改密码
sudo htpasswd /etc/nginx/.htpasswd share
sudo systemctl reload nginx

# 更新代码
cd /srv/kb && git pull
cd student/vue3 && npm ci && npm run build
sudo systemctl restart kb

# 备份数据（SQLite）
sudo systemctl stop kb
cp /srv/kb/student/fast_api/kb.db ~/kb-$(date +%F).db
sudo systemctl start kb

# 或者更简单：走接口导出 JSON（不用停服务）
curl -u share:密码 https://你的域名/api/backup -o kb-backup.json

# 看访问日志（谁在什么时候访问）
sudo tail -f /var/log/nginx/access.log
```

---

## 安全检查清单

部署完逐条对一遍：

- [ ] 后端只监听 `127.0.0.1:8000`，**8000 端口没有对公网开放**
- [ ] 云安全组只放行 22（SSH，最好限定你的 IP）、443（和 80 用于证书续期）
- [ ] 访问 `http://你的IP:8000/api/health` 从外网**打不开**
- [ ] 不带账号访问 `https://你的域名/api/backup` 返回 **401**
- [ ] HTTPS 证书有效（浏览器地址栏有小锁）
- [ ] `/etc/nginx/.htpasswd` 权限是 `644`，属主 root
- [ ] 数据库密码不是 `change_me`
- [ ] `RELOAD=0`、`--workers 1`
- [ ] `.env` 没有被提交到 git（`.gitignore` 里已有 `.env`）

---

## 这套方案的局限

| 局限 | 影响 | 什么时候需要换 |
|---|---|---|
| 共用账号，分不清谁是谁 | 无操作审计 | 要按人记录时 |
| 没有"退出登录" | 换账号要清浏览器缓存 | — |
| 无法细粒度授权 | 进去后人人可读可写 | 要"只读访客"时 |
| 只防"没密码的人" | 密码泄露即失守 | 需要 2FA 时 |

对"几个人共用个人知识库"这个场景，这些局限都可以接受。真需要更细的权限，再上应用层账号体系（JWT + 用户表）。
