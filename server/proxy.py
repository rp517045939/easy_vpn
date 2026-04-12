import logging
from fastapi import Request, Response

logger = logging.getLogger(__name__)

# 不向 Client 转发的 hop-by-hop header
_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


async def proxy_handler(request: Request) -> Response:
    from rules import rules_manager
    from tunnel_manager import tunnel_manager

    host = request.headers.get("host", "").split(":")[0]
    rule = rules_manager.resolve_http(host)

    if not rule:
        return Response(content=f"No tunnel found for: {host}", status_code=404)

    client_id = rule["client_id"]
    if not tunnel_manager.is_online(client_id):
        return Response(content=f"Client '{client_id}' is offline", status_code=503)

    body = await request.body()

    # 过滤 hop-by-hop headers，保留其余
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _HOP_HEADERS
    }

    request_data = {
        "method":       request.method,
        "path":         request.url.path,
        "query_string": str(request.url.query),
        "headers":      headers,
        "body":         body.decode("latin-1") if body else "",
    }

    try:
        resp = await tunnel_manager.forward_http(client_id, request_data)
        resp_headers = {
            k: v for k, v in resp.get("headers", {}).items()
            if k.lower() not in _HOP_HEADERS
        }
        return Response(
            content=resp.get("body", "").encode("latin-1"),
            status_code=resp.get("status_code", 200),
            headers=resp_headers,
        )
    except TimeoutError:
        return Response(content="Tunnel timeout", status_code=504)
    except Exception as e:
        logger.error(f"Proxy error for {host}: {e}")
        return Response(content="Bad Gateway", status_code=502)
