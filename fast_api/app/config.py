"""应用配置：全部通过环境变量 / .env 注入。"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]#设置基地址为当前目录往上走两个，即fast_api文件夹


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "个人知识库"
    app_version: str = "0.1.0"

    # 开发期热重载开关：设 RELOAD=1 打开（默认关闭，避免多进程带来的额外问题）
    reload: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # 数据库：默认 MySQL，可切换成 sqlite:///./kb.db 用于应急演示
    database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/kb_db?charset=utf8mb4"
    test_database_url: str = "mysql+pymysql://root:@127.0.0.1:3306/kb_test?charset=utf8mb4"

    # 倒排索引落盘位置
    index_path: Path = Path("data/index.json")

    # 前端开发服务器地址（CORS 白名单，逗号分隔）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    secret_key: str = "dev-only-secret"

    @field_validator("index_path")
    @classmethod
    def resolve_index_path(cls, path: Path) -> Path:
        return BACKEND_DIR / path

    @field_validator("database_url", "test_database_url")
    @classmethod
    def resolve_sqlite_path(cls, url: str) -> str:
        """把 SQLite 的相对路径固定到 fast_api 目录下。

        否则 `sqlite:///./kb.db` 会跟着启动目录跑：在 fast_api 里启动是一个文件，
        在仓库根目录启动又变另一个，数据像"丢了"。
        """
        prefix = "sqlite:///"
        # 内存库、已写绝对路径（sqlite:////srv/x.db 或 sqlite:///C:/x.db）直接放行
        if not url.startswith(prefix) or url.startswith("sqlite:////") or ":memory:" in url:
            return url

        raw = url[len(prefix) :]
        path = Path(raw)
        if not raw or path.is_absolute():
            return url
        return prefix + (BACKEND_DIR / path).resolve().as_posix()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
