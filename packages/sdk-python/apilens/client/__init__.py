from .client import ApiLensClient, ApiLensConfig
from .models import RequestRecord

# install_apilens_exporter is intentionally NOT imported here (eagerly
# importing .otel would import the real `opentelemetry` package as a side
# effect of `import apilens`, defeating the lazy-import design — see
# apilens/__init__.py's wrapper, which is the public entry point for it).

__all__ = [
    "ApiLensClient",
    "ApiLensConfig",
    "RequestRecord",
]
