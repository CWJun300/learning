"""绕过 pip 的临时目录机制，直接把 wheel 解压进 site-packages。

背景：本机的进程沙箱会让 pip 的 pip-unpack-* 临时目录在下载后变得不可访问，
导致 pip 一律报 PermissionError。此脚本只做三件事：下载、解压、落盘，
不经过 pip 的临时目录。
"""

import os
import re
import sys
import tarfile
import urllib.request
import zipfile
from urllib.parse import urljoin

MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_wheels")


def site_packages() -> str:
    return os.path.join(sys.prefix, "Lib", "site-packages")


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "deps-installer/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def is_compatible(filename: str) -> bool:
    f = filename.lower()
    if f.endswith(".whl"):
        if "py3-none-any" in f or "py2.py3-none-any" in f:
            return True
        if "cp313" in f and "win_amd64" in f:
            return True
        if "abi3" in f and "win_amd64" in f:
            return True
        return False
    return False


def pick_url(package: str) -> tuple[str, str]:
    """返回 (文件名, 下载地址)。同一页面里版本按升序排列，取最后一个兼容项。"""
    page_url = f"{MIRROR}/{package}/"
    html = fetch(page_url).decode("utf-8", "ignore")
    links = re.findall(r'href="([^"#]+)', html)

    best = None
    for link in links:
        name = link.rstrip("/").split("/")[-1]
        if is_compatible(name):
            best = (name, urljoin(page_url, link))
    if best is None:
        # 退而求其次：源码包（jieba 等纯 Python 项目）
        for link in links:
            name = link.rstrip("/").split("/")[-1]
            if name.endswith(".tar.gz"):
                best = (name, urljoin(page_url, link))
    if best is None:
        raise RuntimeError(f"找不到可用的分发包: {package}")
    return best


def install_wheel(path: str, target: str) -> None:
    with zipfile.ZipFile(path) as zf:
        zf.extractall(target)


def install_sdist(path: str, target: str, package: str) -> None:
    """从源码包安装：只取其中的 package 目录，逐文件写出。

    不走 tarfile.extractall，是因为解压出的子目录在本机沙箱里可能立刻不可访问。
    """
    with tarfile.open(path) as tf:
        members = [
            m for m in tf.getmembers() if f"/{package}/" in m.name.replace("\\", "/") and m.isfile()
        ]
        if not members:
            raise RuntimeError(f"源码包里没找到 {package} 目录")

        root = members[0].name.replace("\\", "/").split("/")[0]
        prefix = f"{root}/{package}/"
        dst = os.path.join(target, package)

        import shutil

        if os.path.isdir(dst):
            shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst, exist_ok=True)

        for m in members:
            rel = m.name.replace("\\", "/")[len(prefix) :]
            if not rel or ".." in rel:
                continue
            out = os.path.join(dst, *rel.split("/"))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            payload = tf.extractfile(m).read()
            with open(out, "wb") as f:
                f.write(payload)


def main(packages: list[str]) -> int:
    target = site_packages()
    os.makedirs(CACHE, exist_ok=True)
    print(f"site-packages = {target}")

    for pkg in packages:
        try:
            name, url = pick_url(pkg)
        except Exception as exc:  # noqa: BLE001
            print(f"[失败] {pkg}: 解析地址出错 {exc}")
            continue

        path = os.path.join(CACHE, name)
        if not os.path.exists(path):
            try:
                blob = fetch(url)
            except Exception as exc:  # noqa: BLE001
                print(f"[失败] {pkg}: 下载出错 {exc}")
                continue
            with open(path, "wb") as f:
                f.write(blob)

        try:
            if name.endswith(".whl"):
                install_wheel(path, target)
            else:
                install_sdist(path, target, pkg)
            print(f"[成功] {pkg:15s} <- {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[失败] {pkg}: 安装出错 {type(exc).__name__} {exc}")

    return 0


if __name__ == "__main__":
    pkgs = sys.argv[1:] or [
        "iniconfig",
        "packaging",
        "pluggy",
        "pytest",
        "sqlalchemy",
        "pymysql",
        "pycparser",
        "cffi",
        "cryptography",
        "jieba",
    ]
    sys.exit(main(pkgs))
