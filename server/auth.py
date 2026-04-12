"""
JWT 认证：管理面板登录、Client 注册 token 校验。
"""


def create_access_token(data: dict) -> str:
    pass


def verify_access_token(token: str) -> dict:
    pass


def verify_client_token(token: str) -> bool:
    pass
