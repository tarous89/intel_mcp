"""Private Site.agent routes. Public MCP tools and Engine ownership are unchanged."""
from __future__ import annotations

import asyncio
import json
import logging
import secrets

from starlette.responses import JSONResponse

from intel_mcp.site_search import (
    SiteSearchError,
    create_project_search,
    interpret_context,
    search_deterministically,
)

LOGGER = logging.getLogger("intel_mcp.site_agent")


def register_site_search(mcp, settings, engine_factory):
    semaphore = asyncio.Semaphore(2)

    def response(body, status=200):
        return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})

    def authorized(request) -> bool:
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        configured = settings.report_plan_service_token
        return bool(configured and scheme.casefold() == "bearer" and secrets.compare_digest(supplied.strip(), configured))

    async def request_body(request):
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 60000:
                raise SiteSearchError("Request is too large.", 413)
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeError) as error:
            raise SiteSearchError("A valid JSON object is required.", 400) from error
        if not isinstance(body, dict):
            raise SiteSearchError("A valid JSON object is required.", 400)
        return body

    async def run(request, operation, timeout):
        if not authorized(request):
            return response({"error": "Unauthorized."}, 401)
        acquired = False
        try:
            body = await request_body(request)
            await asyncio.wait_for(semaphore.acquire(), timeout=0.25)
            acquired = True
            async with asyncio.timeout(timeout):
                result = await operation(body)
            return response(result)
        except SiteSearchError as error:
            return response({"error": str(error)}, error.status)
        except TimeoutError:
            return response({"error": "The search service is busy. Please retry."}, 429 if not acquired else 503)
        except Exception as error:
            LOGGER.warning("Site.agent failed: %s", type(error).__name__)
            return response({"error": "The search could not be completed. Please retry."}, 503)
        finally:
            if acquired:
                semaphore.release()

    @mcp.custom_route("/internal/site-agent/interpret", methods=["POST"])
    async def site_interpret(request):
        async def operation(body):
            criteria, usage = await interpret_context(settings, body.get("context"))
            return {"criteria": criteria, "usage": usage}
        return await run(request, operation, 100)

    @mcp.custom_route("/internal/site-agent/search", methods=["POST"])
    async def site_search(request):
        async def operation(body):
            if "criteria" in body:
                return await search_deterministically(engine_factory(), body["criteria"])
            # Compatibility for the existing deployed app during a rolling release.
            return await create_project_search(settings, engine_factory(), body)
        return await run(request, operation, 300)

    return site_search
