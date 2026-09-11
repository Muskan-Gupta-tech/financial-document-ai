import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import init_db

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    init_db()


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "connected")
    assert data["database"] == "connected"
    assert "version" in data


def test_process_invoice_api():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sample_path = os.path.join(base_dir, "data", "sample_documents", "sample_invoice.jpg")

    assert os.path.exists(sample_path), f"Sample file not found at {sample_path}"

    with open(sample_path, "rb") as f:
        files = {"file": ("sample_invoice.jpg", f, "image/jpeg")}
        data = {"document_type": "invoice"}
        response = client.post("/api/v1/documents/process", files=files, data=data)

    assert response.status_code == 200
    res = response.json()
    assert res["document_name"] == "sample_invoice.jpg"
    assert res["document_type"] == "invoice"
    assert res["processing_status"] == "PASS"
    assert res["file_validation"]["status"] == "PASS"
    assert res["extracted_data"]["total_amount"]["value"] == 138.90
    assert res["validation"]["overall_status"] == "PASS"


def test_get_document_by_name_api():
    # Retrieve the document processed in previous test
    response = client.get("/api/v1/documents/sample_invoice.jpg")
    assert response.status_code == 200
    res = response.json()
    assert res["document_name"] == "sample_invoice.jpg"
    assert res["document_type"] == "invoice"


def test_list_documents_api():
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    res = response.json()
    assert "total" in res
    assert res["total"] >= 1
    assert len(res["documents"]) >= 1


def test_serve_dashboard_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "FinEdge AI" in response.text


def test_serve_document_result_html():
    response = client.get("/documents/sample_invoice.jpg/view")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "sample_invoice.jpg" in response.text


def test_unsupported_file_type_api():
    files = {"file": ("script.sh", b"echo 'hello'", "text/plain")}
    data = {"document_type": "invoice"}
    response = client.post("/api/v1/documents/process", files=files, data=data)
    assert response.status_code == 400
    res = response.json()
    assert "error" in res
    assert res["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_document_not_found_api():
    response = client.get("/api/v1/documents/non_existent_document_12345.pdf")
    assert response.status_code == 404
    res = response.json()
    assert res["error"]["code"] == "DOCUMENT_NOT_FOUND"
