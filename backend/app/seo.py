"""robots.txt and sitemap.xml, so search engines can find the public pages.

Both are built from APP_BASE_URL (on Render, the service's public address), so they stay
correct if the address changes, for example when a custom domain is added.

Only production asks to be indexed. Every other environment (a staging server, a laptop)
tells search engines to stay away, so test copies never show up in search results.
"""

from xml.sax.saxutils import escape

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, Response

from app.core.config import Settings

# Public pages worth finding in a search. Everything under /app needs an account, and
# /api is for the app itself, so neither is listed or crawled.
PUBLIC_PAGES = ("/", "/guide", "/register")
CACHE_FOR_A_DAY = "public, max-age=86400"


def robots_txt(settings: Settings) -> str:
    if settings.environment != "production":
        return "User-agent: *\nDisallow: /\n"
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /app\n"
        "Disallow: /api/\n"
        f"Sitemap: {settings.app_base_url}/sitemap.xml\n"
    )


def sitemap_xml(settings: Settings) -> str:
    urls = "".join(
        f"  <url><loc>{escape(settings.app_base_url + page)}</loc></url>\n" for page in PUBLIC_PAGES
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}"
        "</urlset>\n"
    )


def install_search_routes(app: FastAPI, settings: Settings) -> None:
    """Add /robots.txt and /sitemap.xml. Call before the frontend's catch-all route."""
    robots = robots_txt(settings)
    sitemap = sitemap_xml(settings)

    @app.get("/robots.txt", include_in_schema=False)
    async def robots_route() -> PlainTextResponse:
        return PlainTextResponse(robots, headers={"cache-control": CACHE_FOR_A_DAY})

    @app.get("/sitemap.xml", include_in_schema=False)
    async def sitemap_route() -> Response:
        return Response(
            sitemap, media_type="application/xml", headers={"cache-control": CACHE_FOR_A_DAY}
        )
