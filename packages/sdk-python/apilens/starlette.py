from __future__ import annotations

from typing import Any, Callable

from .client import ApiLensClient
from .client._routes import starlette_route_template
from .client.middleware import ApiLensASGIMiddleware, set_consumer, track_consumer


def instrument_app(
    app,
    client: ApiLensClient,
    *,
    project_slug: str = "",
    app_id: str = "",
    environment: str | None = None,
    log_request_body: bool = True,
    log_response_body: bool = True,
    capture_payloads: bool = True,
    capture_headers: bool = True,
    capture_spans: bool = True,
    service_name: str = "",
    max_payload_bytes: int = 65536,
    get_consumer: Callable[..., Any] | None = None,
):
    """Starlette integration via ASGI middleware."""
    app.add_middleware(
        ApiLensASGIMiddleware,
        client=client,
        project_slug=project_slug,
        app_id=app_id,
        environment=environment,
        log_request_body=log_request_body,
        log_response_body=log_response_body,
        capture_payloads=capture_payloads,
        capture_headers=capture_headers,
        capture_spans=capture_spans,
        service_name=service_name,
        max_payload_bytes=max_payload_bytes,
        get_consumer=get_consumer,
        route_resolver=starlette_route_template,
    )
    return app


__all__ = ["instrument_app", "track_consumer", "set_consumer"]
