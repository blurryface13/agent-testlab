"""Read-only Requests smoke checks for a running Asteria API."""
from __future__ import annotations

import os

import requests


BASE_URL = os.getenv("ASTERIA_BASE_URL", "http://127.0.0.1:8018").rstrip("/")


def test_asteria_openapi_and_discovery_are_reachable():
    session = requests.Session()
    openapi = session.get(f"{BASE_URL}/openapi.json", timeout=10)
    assert openapi.status_code == 200, openapi.text[:300]
    paths = set(openapi.json().get("paths", {}))
    assert "/api/coordinator/route" in paths
    assert "/api/workspace/runs" in paths
    assert "/api/evaluation/monitor" in paths

    discovery = session.get(f"{BASE_URL}/.well-known/agent-discovery.json", timeout=10)
    assert discovery.status_code == 200, discovery.text[:300]
    assert discovery.json().get("services")
