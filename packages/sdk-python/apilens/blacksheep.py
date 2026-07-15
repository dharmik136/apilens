from __future__ import annotations

from .client import ApiLensClient
from .client._routes import blacksheep_route_template, blacksheep_set_route_pattern
from .client.middleware import ApiLensASGIMiddleware


def _instrument_router(app) -> None:
    """Wrap ``app.router.get_match`` to record the matched route pattern.

    BlackSheep only exposes the template here; we stash it in a contextvar the
    ASGI middleware reads back. Idempotent — installing twice is a no-op.
    """
    router = getattr(app, "router", None)
    if router is None or getattr(router, "_apilens_wrapped", False):
        return
    original_get_match = router.get_match

    def _wrapped_get_match(request):
        match = original_get_match(request)
        try:
            pattern = match.pattern.decode() if match is not None else None
        except Exception:
            pattern = None
        blacksheep_set_route_pattern(pattern)
        return match

    router.get_match = _wrapped_get_match  # type: ignore[assignment]
    router._apilens_wrapped = True  # type: ignore[attr-defined]


def instrument_app(
    app,
    client: ApiLensClient,
    *,
    app_id: str = "",
    project_slug: str = "",
    environment: str | None = None,
    log_request_body: bool = True,
    log_response_body: bool = True,
    capture_payloads: bool = True,
    capture_headers: bool = True,
    capture_spans: bool = True,
    service_name: str = "",
    max_payload_bytes: int = 65536,
):
    """BlackSheep integration via ASGI middleware.

    ``app_id`` selects which app in the project the traffic belongs to and is
    required for ingestion (and for span capture). Pass ``capture_spans=False``
    to record requests without emitting trace spans.
    """
    _instrument_router(app)
    kwargs = dict(
        client=client,
        app_id=app_id,
        project_slug=project_slug,
        environment=environment,
        log_request_body=log_request_body,
        log_response_body=log_response_body,
        capture_payloads=capture_payloads,
        capture_headers=capture_headers,
        capture_spans=capture_spans,
        service_name=service_name,
        max_payload_bytes=max_payload_bytes,
        route_resolver=blacksheep_route_template,
    )
    if hasattr(app, "asgi"):
        app.asgi = ApiLensASGIMiddleware(app.asgi, **kwargs)
    elif hasattr(app, "_asgi_app"):
        app._asgi_app = ApiLensASGIMiddleware(app._asgi_app, **kwargs)  # noqa: SLF001
    else:
        raise RuntimeError("Unsupported BlackSheep app shape for middleware installation")
    return app
