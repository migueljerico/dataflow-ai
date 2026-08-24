import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.open_data_service import OpenDataService, FEATURED_OPEN_DATASETS

client = TestClient(app)


def test_get_featured_open_datasets():
    response = client.get("/api/v1/datasets/open-data/featured")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    first = data[0]
    assert "id" in first
    assert "title" in first
    assert "resource_url" in first
    assert first["resource_url"].startswith(("http://", "https://"))
    assert first["format"] in ("CSV", "XLSX")


def test_search_open_datasets_empty_query():
    response = client.get("/api/v1/datasets/open-data/search")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["results"]) > 0
    assert "source" in data


def test_search_open_datasets_curated_match():
    response = client.get("/api/v1/datasets/open-data/search?query=pib")
    assert response.status_code == 200
    data = response.json()
    assert any("pib" in item["title"].lower() or "pib" in item["description"].lower() for item in data["results"])


def test_search_open_datasets_ckan_integration_mock():
    mock_ckan_response = {
        "success": True,
        "result": {
            "count": 1,
            "results": [
                {
                    "id": "traffic-madrid-2026",
                    "title": "Aforos de Tráfico Urbano",
                    "notes": "Intensidad y velocidad media de vehículos en puntos de control.",
                    "organization": {
                        "title": "Ayuntamiento de Madrid",
                        "name": "ayto-madrid"
                    },
                    "tags": [{"name": "tráfico"}, {"name": "movilidad"}],
                    "resources": [
                        {
                            "id": "res-12345",
                            "name": "aforos_2026.csv",
                            "format": "CSV",
                            "url": "https://opendata.madrid.es/data/aforos_2026.csv",
                            "size": 1048576
                        }
                    ]
                }
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_ckan_response

    with patch("app.services.open_data_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        response = client.get("/api/v1/datasets/open-data/search?query=aforos")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        ckan_item = next((i for i in data["results"] if i["id"].startswith("ckan-")), None)
        assert ckan_item is not None
        assert ckan_item["title"] == "Aforos de Tráfico Urbano"
        assert ckan_item["organization"] == "Ayuntamiento de Madrid"
        assert ckan_item["resource_url"] == "https://opendata.madrid.es/data/aforos_2026.csv"
        assert ckan_item["format"] == "CSV"


def test_search_open_datasets_ckan_network_error_graceful_fallback():
    with patch("app.services.open_data_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused / Timeout")
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client_cls.return_value.__aexit__.return_value = None

        response = client.get("/api/v1/datasets/open-data/search?query=transporte")
        assert response.status_code == 200
        data = response.json()
        # Debe responder con las coincidencias del catálogo local sin romper
        assert isinstance(data["results"], list)
