"""Managed Agents transport. Credentials never enter the execution environment.

Create idle sessions, persist their IDs, then submit idempotent turn events. A
lost create response must be reconciled by metadata before another create.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from intel_mcp.max_agent_evidence import canonical

TOOLS = ("filter_trials", "get_profiles", "get_documents")


def scoped_token(secret: str, run_id: str) -> str:
    if not secret:
        raise ValueError("Missing scoped MCP signing secret")
    return "max1_" + hmac.new(secret.encode(), f"max-agent:{run_id}".encode(), hashlib.sha256).hexdigest()


class ManagedAgentError(Exception):
    def __init__(self, code, retryable=False):
        super().__init__(code)
        self.code, self.retryable = code, retryable


class ManagedAgent:
    def __init__(self, settings, config, *, transport=None):
        self.settings, self.config, self.transport = settings, config, transport

    def _headers(self):
        return {"Authorization": f"Bearer {self.settings.openai_api_key}", "OpenAI-Beta": "agents=v1"}

    async def _request(self, method, path, *, body=None, key=None):
        headers = self._headers()
        if key:
            headers["Idempotency-Key"] = key
        async with httpx.AsyncClient(transport=self.transport, timeout=60) as client:
            try:
                response = await client.request(method, self.settings.openai_base_url + path, headers=headers, json=body)
            except httpx.HTTPError as error:
                raise ManagedAgentError("AGENT_NETWORK_UNAVAILABLE", True) from error
        if response.is_error:
            if response.status_code == 404 and path.startswith("/agents/sessions/"):
                raise ManagedAgentError("AGENT_SESSION_NOT_FOUND")
            try:
                code = response.json().get("error", {}).get("code", "")
            except (ValueError, AttributeError):
                code = ""
            if code in {"insufficient_quota", "billing_hard_limit_reached", "billing_not_active"}:
                raise ManagedAgentError("AGENT_BILLING_UNAVAILABLE")
            raise ManagedAgentError("AGENT_API_UNAVAILABLE", response.status_code in {408, 409, 429} or response.status_code >= 500)
        return response.json() if response.content else {}

    async def preflight(self):
        """Read-only account capability check; no paid session or model request."""
        self.config.validate(self.settings)
        return await self._request("GET", "/agents/sessions?limit=1")

    async def find_session(self, intent: str):
        path = "/agents/sessions?limit=100&order=desc"
        while path:
            page = await self._request("GET", path)
            matches = [s for s in page.get("data", []) if s.get("metadata", {}).get("max_intent") == intent]
            if matches:
                return min(matches, key=lambda s: (s["created_at"], s["id"]))
            after = page.get("last_id")
            path = "/agents/sessions?limit=100&order=desc&after=" + quote(after, safe="") if page.get("has_more") and after else None
        return None

    async def upload_input(self, name: str, data: bytes):
        """Upload a large input; persist its ID before attempting session creation."""
        if len(data) > 50 * 1024 * 1024:
            raise ManagedAgentError("AGENT_INPUT_TOO_LARGE")
        async with httpx.AsyncClient(transport=self.transport, timeout=120) as client:
            try:
                response = await client.post(self.settings.openai_base_url + "/files", headers=self._headers(),
                    data={"purpose": "user_data"}, files={"file": (name, data, "application/octet-stream")})
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise ManagedAgentError("AGENT_FILE_UPLOAD_UNAVAILABLE", error.response.status_code >= 500) from error
            except httpx.HTTPError as error:
                raise ManagedAgentError("AGENT_NETWORK_UNAVAILABLE", True) from error
        return response.json()["id"]

    async def create_idle(self, run_id: str, intent: str, instructions: str, files: dict[str, bytes], file_refs=None):
        self.config.validate(self.settings)
        file_refs = file_refs or {}
        if len(files) > 50 or sum(len(data) for name, data in files.items() if name not in file_refs) > 10 * 1024 * 1024:
            raise ManagedAgentError("AGENT_INPUT_REQUIRES_FILE_UPLOAD")
        inputs = []
        for name, data in files.items():
            if not re.fullmatch(r"[a-zA-Z0-9_.-]+", name):
                raise ManagedAgentError("AGENT_INPUT_INVALID_NAME")
            if name in file_refs:
                inputs.append({"type": "file_id", "path": "/workspace/" + name, "file_id": file_refs[name]})
                continue
            if len(data) > 5 * 1024 * 1024:
                raise ManagedAgentError("AGENT_INPUT_REQUIRES_FILE_UPLOAD")
            inputs.append({"type": "inline", "path": "/workspace/" + name,
                           "data": base64.b64encode(data).decode("ascii")})
        url = self.settings.mcp_public_resource_url.removesuffix("/mcp") + f"/max-agent/mcp/{run_id}"
        return await self._request("POST", "/agents/sessions", body={
            "agent": {"model": self.config.model, "instructions": instructions,
                      "multi_agent": {"enabled": False},
                      "tools": [{"type": "mcp", "server_label": "report_evidence",
                                 "transport": {"type": "http", "server_url": url,
                                               "authorization": "Bearer " + scoped_token(self.settings.app_service_token, run_id)},
                                 "connection_origin": "service", "required": True,
                                 "allowed_tools": list(TOOLS)}]},
            "environment": {"type": "openai_hosted", "files": inputs, "network": {"access": "disabled"}},
            "metadata": {"max_report": run_id, "max_intent": intent},
        })

    async def send(self, session_id: str, text: str, intent: str):
        # Only this mutation has a documented idempotency guarantee.
        return await self._request("POST", f"/agents/sessions/{quote(session_id, safe='')}/events", key=intent,
            body={"events": [{"type": "agent.session.input.message", "input": [
                {"role": "user", "content": [{"type": "input_text", "text": text}]}]}]})

    async def inspect(self, session_id: str):
        sid = quote(session_id, safe="")
        session = await self._request("GET", f"/agents/sessions/{sid}")
        turns = await self._request("GET", f"/agents/sessions/{sid}/turns?limit=100&order=desc")
        return session, [t for t in turns.get("data", []) if not t.get("subagent_id")]

    async def cancel(self, session_id: str):
        return await self._request("POST", f"/agents/sessions/{quote(session_id, safe='')}/events",
                                   body={"events": [{"type": "agent.session.input.cancel"}]})

    async def artifacts(self, session_id: str, turn_id: str):
        sid = quote(session_id, safe="")
        path = f"/agents/sessions/{sid}/artifacts?limit=100"
        result = []
        while path:
            page = await self._request("GET", path)
            result.extend(a for a in page.get("data", []) if a.get("turn_id") == turn_id)
            after = page.get("last_id")
            path = f"/agents/sessions/{sid}/artifacts?limit=100&after={quote(after, safe='')}" if page.get("has_more") and after else None
        return result

    async def download(self, session_id: str, artifact_id: str, target: Path, limit: int = 32 * 1024 * 1024):
        url = self.settings.openai_base_url + f"/agents/sessions/{quote(session_id, safe='')}/artifacts/{quote(artifact_id, safe='')}/content"
        async with httpx.AsyncClient(transport=self.transport, timeout=120) as client:
            async with client.stream("GET", url, headers=self._headers()) as response:
                response.raise_for_status()
                size = 0
                with target.open("wb") as output:
                    async for chunk in response.aiter_bytes(65536):
                        size += len(chunk)
                        if size > limit:
                            raise ManagedAgentError("AGENT_ARTIFACT_TOO_LARGE")
                        output.write(chunk)
