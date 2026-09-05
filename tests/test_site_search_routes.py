import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient
from intel_mcp.site_search_routes import register_site_search

class Registry:
    def __init__(self): self.routes = []
    def custom_route(self, path, methods):
        def decorator(fn):
            self.routes.append(Route(path, fn, methods=methods))
            return fn
        return decorator

class RouteTests(unittest.TestCase):
    def setUp(self):
        registry = Registry()
        register_site_search(registry, SimpleNamespace(report_plan_service_token="test-secret"), lambda: object())
        self.client = TestClient(Starlette(routes=registry.routes))

    def test_unauthorized_does_not_run_search(self):
        with patch("intel_mcp.site_search_routes.search_investigators", new_callable=AsyncMock) as search:
            response = self.client.post("/internal/site-agent/search", json={"context": "NSCLC trial context"})
            self.assertEqual(response.status_code, 401)
            search.assert_not_called()

    def test_oversize_chunked_body_rejected(self):
        response = self.client.post("/internal/site-agent/search", content=b"x" * 60001, headers={"Authorization": "Bearer test-secret"})
        self.assertEqual(response.status_code, 413)

    def test_authorized_result_is_not_cached(self):
        with patch("intel_mcp.site_search_routes.search_investigators", new_callable=AsyncMock, return_value={"rows": []}):
            response = self.client.post("/internal/site-agent/search", json={"context": "NSCLC trial context"}, headers={"Authorization": "Bearer test-secret"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_internal_exception_is_not_exposed(self):
        with patch("intel_mcp.site_search_routes.search_investigators", new_callable=AsyncMock, side_effect=RuntimeError("private secret")):
            response = self.client.post("/internal/site-agent/search", json={}, headers={"Authorization": "Bearer test-secret"})
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("private secret", response.text)
