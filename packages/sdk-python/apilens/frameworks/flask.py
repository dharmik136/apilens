from __future__ import annotations

from typing import Any, Callable

from ..client import ApiLensClient
from ..client._routes import flask_route_template
from ..client.middleware import ApiLensWSGIMiddleware, set_consumer, track_consumer


def instrument_flask(
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
    """Flask integration via WSGI wrapper.

    **Minimal setup**::

        from flask import Flask
        from apilens import ApiLensClient, ApiLensConfig
        from apilens.flask import instrument_flask

        app = Flask(__name__)
        client = ApiLensClient(ApiLensConfig(api_key="apilens_xxx"))
        instrument_flask(app, client, app_id="my-flask-app")

    **Identifying consumers** — call :func:`set_consumer` from a
    ``before_request`` hook (no ``request`` argument needed; it uses a
    contextvar that the middleware reads at response time)::

        from flask import Flask, g
        from apilens.flask import instrument_flask, set_consumer

        @app.before_request
        def identify_consumer():
            if g.current_user:                      # however YOUR app sets this
                set_consumer(
                    identifier=g.current_user["email"],   # required: stable id
                    name=g.current_user.get("name"),      # optional: display name
                    group=g.current_user.get("role"),     # optional: team/tier/org
                )

    **Centralized resolver** — resolve from the WSGI environ (alternative)::

        instrument_flask(
            app, client, app_id="my-flask-app",
            get_consumer=lambda environ: environ.get("HTTP_X_USER_ID"),
        )
    """
    # Close over the Flask app so the resolver can match the WSGI environ
    # against its url_map (rule.rule → /product/<int:id> → /product/{id}).
    app.wsgi_app = ApiLensWSGIMiddleware(  # type: ignore[assignment]
        app.wsgi_app,
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
        route_resolver=lambda environ: flask_route_template(app, environ),
    )
    return app


__all__ = ["instrument_flask", "track_consumer", "set_consumer"]
