"""
从环境变量读取配置，所有敏感值通过 .env 注入，不硬编码。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 服务监听
    host: str = "0.0.0.0"
    port: int = 8080

    # 认证
    secret_key: str          # JWT 签名密钥，必填
    admin_username: str      # 管理面板用户名，必填
    admin_password: str      # 管理面板密码，必填
    token_expire_minutes: int = 60 * 24

    # 隧道
    client_token: str        # Client 注册时使用的共享 token，必填

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
