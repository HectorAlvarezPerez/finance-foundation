from urllib.parse import urlencode, urljoin


def sanitize_next_path(next_path: str) -> str:
    if not next_path.startswith("/") or next_path.startswith("//"):
        return "/app"

    return next_path


def build_frontend_redirect_url(
    *,
    default_frontend_origin: str,
    next_path: str,
    error: str | None = None,
) -> str:
    sanitized_next_path = sanitize_next_path(next_path)
    target = urljoin(default_frontend_origin, sanitized_next_path)
    if error is None:
        return target

    login_url = urljoin(default_frontend_origin, "/login")
    query = urlencode({"error": error, "next": sanitized_next_path})
    return f"{login_url}?{query}"
