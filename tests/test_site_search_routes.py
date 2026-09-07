import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from intel_mcp.site_search_routes import register_site_search


class Registry:
    def __init__(self):
        self.routes = []

    def custom_route(self, path, methods):
        def decorator(function):
            self.routes.append(Route(path, function, methods=methods))
            return function
        return decorator


class RouteTests(unittest.TestCase):
    def setUp(self):
        registry = Registry()
        register_site_search(registry, SimpleNamespace(report_plan_service_token="test-secret"), lambda: object())
        self.client = TestClient(Starlette(routes=registry.routes))
        self.headers = {"Authorization": "Bearer test-secret"}

    def test_unauthorized_does_not_run_planner(self):
        with patch("intel_mcp.site_search_routes.interpret_context", new_callable=AsyncMock) as planner:
            response = self.client.post("/internal/site-agent/interpret", json={"context": "NSCLC trial context"})
            self.assertEqual(response.status_code, 401)
            planner.assert_not_called()

    def test_oversize_body_is_rejected(self):
        response = self.client.post(
            "/internal/site-agent/search", content=b"x" * 60001, headers=self.headers,
        )
        self.assertEqual(response.status_code, 413)

    def test_interpret_route_returns_storable_criteria_and_usage(self):
        with patch(
            "intel_mcp.site_search_routes.interpret_context", new_callable=AsyncMock,
            return_value=({"therapeutic_areas": ["Neurology"], "keywords": ["migraine"]}, {"model": "terra"}),
        ):
            response = self.client.post(
                "/internal/site-agent/interpret", json={"context": "Preventive migraine study"}, headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["criteria"]["keywords"], ["migraine"])
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_search_route_with_stored_criteria_is_model_free(self):
        with patch("intel_mcp.site_search_routes.search_deterministically", new_callable=AsyncMock, return_value={"sites": [], "pis": []}) as search, patch("intel_mcp.site_search_routes.interpret_context", new_callable=AsyncMock) as planner:
            response = self.client.post(
                "/internal/site-agent/search",
                json={"criteria": {"therapeutic_areas": ["Neurology"], "keywords": ["migraine"]}},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        search.assert_awaited_once()
        planner.assert_not_called()

    def test_internal_exception_is_not_exposed(self):
        with patch("intel_mcp.site_search_routes.search_deterministically", new_callable=AsyncMock, side_effect=RuntimeError("private secret")):
            response = self.client.post(
                "/internal/site-agent/search",
                json={"criteria": {"therapeutic_areas": ["Neurology"], "keywords": ["migraine"]}},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private secret", response.text)
