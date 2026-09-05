"""Private, bounded Site.agent route. Public MCP report tools are unchanged."""
from __future__ import annotations
import asyncio
import json
import logging
import secrets
from starlette.responses import JSONResponse
from intel_mcp.site_search import SiteSearchError, search_investigators

LOGGER = logging.getLogger("intel_mcp.site_agent")


def register_site_search(mcp, settings, engine_factory):
    semaphore = asyncio.Semaphore(2)

    def response(body, status=200):
        return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})

    @mcp.custom_route("/internal/site-agent/search", methods=["POST"])
    async def site_search(request):
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        configured = settings.report_plan_service_token
        if not configured or scheme.casefold() != "bearer" or not secrets.compare_digest(supplied.strip(), configured):
            return response({"error": "Unauthorized."}, 401)
        try:
            raw = bytearray()
            async for chunk in request.stream():
                raw.extend(chunk)
                if len(raw) > 60000:
                    return response({"error": "Request is too large."}, 413)
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, UnicodeError):
            return response({"error": "A valid JSON object is required."}, 400)
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=0.25)
        except TimeoutError:
            return response({"error": "The search service is busy. Please retry."}, 429)
        try:
            async with asyncio.timeout(150):
                result = await search_investigators(settings, engine_factory(), body)
            return response(result)
        except SiteSearchError as error:
            return response({"error": str(error)}, error.status)
        except TimeoutError:
            return response({"error": "The search timed out. Please retry."}, 503)
        except Exception as error:
            LOGGER.warning("Site.agent failed: %s", type(error).__name__)
            return response({"error": "The search could not be completed. Please retry."}, 503)
        finally:
            semaphore.release()
    return site_search
