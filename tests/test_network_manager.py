"""
tests/test_network_manager.py — Unit tests for Network Settings / Wi-Fi Manager
"""

import pytest
from fastapi.testclient import TestClient
from server.services.api_service.service import ApiService
from server.services.network_manager import get_network_status, scan_wifi_networks, connect_wifi

def test_get_network_status_structure():
    status = get_network_status()
    assert "ssid" in status
    assert status["hostname"] == "sentinelpi.local"
    assert "ip" in status
    assert "mqtt" in status
    assert status["websocket_port"] == 9001
    assert "network_connected" in status

def test_scan_wifi_networks():
    networks = scan_wifi_networks()
    assert isinstance(networks, list)
    assert len(networks) > 0
    # Verify deduplication
    assert len(networks) == len(set(networks))

def test_connect_wifi_validation():
    # Empty SSID should fail validation
    res = connect_wifi("", "password")
    assert res["status"] == "error"

def test_connect_wifi_valid_format():
    res = connect_wifi("ATL LAB", "testpass")
    assert res["status"] in ["success", "error"]
    assert "message" in res

def test_api_network_endpoints():
    api_service = ApiService()
    client = TestClient(api_service.app)

    # 1. GET /api/network/status
    res_status = client.get("/api/network/status")
    assert res_status.status_code == 200
    data_status = res_status.json()
    assert data_status["hostname"] == "sentinelpi.local"

    # 2. GET /api/network/scan
    res_scan = client.get("/api/network/scan")
    assert res_scan.status_code == 200
    data_scan = res_scan.json()
    assert "networks" in data_scan
    assert isinstance(data_scan["networks"], list)

    # 3. POST /api/network/connect
    res_connect = client.post(
        "/api/network/connect",
        json={"ssid": "ATL LAB", "password": "secret_password"}
    )
    assert res_connect.status_code == 200
    data_connect = res_connect.json()
    assert data_connect["status"] == "success"
    # Verify password is NOT exposed in response payload
    assert "password" not in data_connect
