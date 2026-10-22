"""Read-only Midnight connectivity checks. No node, wallet, or /prove call."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from Backend.main import app
from Backend.midnight_client import MidnightClient, _CONNECTIVITY_TIMEOUT_SECONDS


class _Response:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "http://midnight.test/health")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self) -> object:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _Client:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.timeout = None
        self.calls: list[tuple[str, str]] = []

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get(self, url: str) -> _Response:
        self.calls.append(("GET", url))
        return self.response


def _run(client: MidnightClient) -> dict:
    return asyncio.run(client.service_health())


class MidnightConnectivityTests(unittest.TestCase):
    def _client(self) -> MidnightClient:
        client = MidnightClient()
        client.base_url = "http://midnight.test"
        return client

    def test_unconfigured_client_makes_no_request(self) -> None:
        client = MidnightClient()
        client.base_url = ""
        with patch("Backend.midnight_client.httpx.AsyncClient") as async_client:
            result = _run(client)
        async_client.assert_not_called()
        self.assertEqual(
            result,
            {
                "midnight_configured": False,
                "midnight_reachable": False,
                "midnight_status": "not_configured",
            },
        )

    def test_health_get_reports_reachable_service(self) -> None:
        holder: dict[str, _Client] = {}

        def factory(*args, **kwargs):
            del args
            client = _Client(
                _Response(
                    {
                        "status": "ok",
                        "contract_configured": True,
                        "compiled_contract_configured": True,
                        "wallet_configured": True,
                        "network": "undeployed",
                        "extra": "http://user:secret@example",
                    }
                )
            )
            client.timeout = kwargs.get("timeout")
            holder["client"] = client
            return client

        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=factory):
            result = _run(self._client())

        self.assertEqual(holder["client"].timeout, _CONNECTIVITY_TIMEOUT_SECONDS)
        self.assertEqual(holder["client"].calls, [("GET", "http://midnight.test/health")])
        self.assertEqual(result["midnight_status"], "ok")
        self.assertTrue(result["midnight_reachable"])
        self.assertTrue(result["contract_configured"])
        self.assertEqual(result["network"], "undeployed")
        self.assertNotIn("extra", result)

    def test_connection_failure_is_unreachable(self) -> None:
        def factory(*args, **kwargs):
            del args, kwargs
            client = _Client(_Response({}))

            async def fail(url: str) -> _Response:
                client.calls.append(("GET", url))
                raise httpx.ConnectError("connection refused")

            client.get = fail
            return client

        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=factory):
            result = _run(self._client())
        self.assertEqual(result["midnight_status"], "unreachable")
        self.assertFalse(result["midnight_reachable"])
        self.assertTrue(result["midnight_configured"])

    def test_timeout_is_unreachable(self) -> None:
        def factory(*args, **kwargs):
            del args, kwargs
            client = _Client(_Response({}))

            async def fail(url: str) -> _Response:
                client.calls.append(("GET", url))
                raise httpx.TimeoutException("timed out")

            client.get = fail
            return client

        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=factory):
            result = _run(self._client())
        self.assertEqual(result["midnight_status"], "unreachable")

    def test_http_error_is_unreachable(self) -> None:
        def factory(*args, **kwargs):
            del args, kwargs
            return _Client(_Response({"status": "ok"}, status_code=503))

        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=factory):
            result = _run(self._client())
        self.assertEqual(result["midnight_status"], "unreachable")

    def test_non_ok_status_is_unhealthy_without_crashing(self) -> None:
        def factory(*args, **kwargs):
            del args, kwargs
            return _Client(_Response({"status": "degraded"}))

        with patch("Backend.midnight_client.httpx.AsyncClient", side_effect=factory):
            result = _run(self._client())
        self.assertEqual(result["midnight_status"], "unhealthy")
        self.assertTrue(result["midnight_reachable"])

    def test_api_route_is_read_only_and_preserves_liveness(self) -> None:
        payload = {
            "midnight_configured": True,
            "midnight_reachable": True,
            "midnight_status": "ok",
            "network": "undeployed",
        }
        with patch.object(MidnightClient, "service_health", new=AsyncMock(return_value=payload)):
            client = TestClient(app)
            health = client.get("/health")
            midnight = client.get("/midnight/health")
        self.assertEqual(health.status_code, 200)
        health_body = health.json()
        self.assertEqual(health_body["status"], "healthy")
        self.assertIn("persistence", health_body)
        self.assertIn("midnight_configured", health_body)
        self.assertNotIn("postgres://", health.text)
        self.assertEqual(midnight.status_code, 200)
        self.assertEqual(midnight.json(), payload)


if __name__ == "__main__":
    unittest.main()
