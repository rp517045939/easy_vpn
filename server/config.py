from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080

    secret_key: str
    admin_username: str
    admin_password: str
    token_expire_minutes: int = 60 * 24

    client_token: str

    # 管理面板的域名，用于区分面板请求和隧道请求
    panel_host: str = "vpn.ruanpengpeng.cn"

    # HTTP 隧道子域名的根域名（UI 中显示的后缀，如 .vpn.ruanpengpeng.cn）
    http_domain: str = "vpn.ruanpengpeng.cn"

    # TCP 隧道端口范围
    tcp_port_min: int = 2200
    tcp_port_max: int = 2299

    # 心跳间隔（秒）
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 90

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
