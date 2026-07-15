from __future__ import annotations

from dataclasses import dataclass

from .client import ApiLensClient
from .client._routes import litestar_route_template
from .client.middleware import ApiLensASGIMiddleware


# eq=False keeps identity hashing — Litestar stores plugins in a frozenset, so
# the plugin must be hashable (the default dataclass __eq__ makes it unhashable).
@dataclass(slots=True, eq=False)
class ApiLensPlugin:
    """Litestar plugin-protocol style integration.

    Usage::

        app = Litestar(
            route_handlers=[...],
            plugins=[ApiLensPlugin(client=client, app_id="orders-api")],
        )

    ``app_id`` selects which app in the project the traffic belongs to and is
    required for ingestion (and for span capture).
    """

    client: ApiLensClient
    app_id: str = ""
    project_slug: str = ""
    environment: str | None = None
    log_request_body: bool = True
    log_response_body: bool = True
    capture_payloads: bool = True
    capture_headers: bool = True
    capture_spans: bool = True
    service_name: str = ""
    max_payload_bytes: int = 65536

    def on_app_init(self, app_config):
        try:
            from litestar.middleware import DefineMiddleware
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Litestar integration requires litestar installed in this app environment"
            ) from exc

        middleware = list(getattr(app_config, "middleware", []) or [])
        middleware.append(
            DefineMiddleware(
                ApiLensASGIMiddleware,
                client=self.client,
                app_id=self.app_id,
                project_slug=self.project_slug,
                environment=self.environment,
                log_request_body=self.log_request_body,
                log_response_body=self.log_response_body,
                capture_payloads=self.capture_payloads,
                capture_headers=self.capture_headers,
                capture_spans=self.capture_spans,
                service_name=self.service_name,
                max_payload_bytes=self.max_payload_bytes,
                route_resolver=litestar_route_template,
            )
        )
        app_config.middleware = middleware
        return app_config


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
    """Fallback direct installation for Litestar ASGI apps."""
    app.asgi_handler = ApiLensASGIMiddleware(
        app.asgi_handler,
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
        route_resolver=litestar_route_template,
    )
    return app
