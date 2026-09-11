import os
import pytest
from backend.app.services.extraction_service import ExtractionService


@pytest.fixture
def extraction_service():
    return ExtractionService()


def test_invoice_extraction(extraction_service):
    mock_ocr = [
        {"page": 1, "text": "Invoice no: 94404257", "score": 0.98},
        {"page": 1, "text": "Date of issue: 07/03/2013", "score": 0.99},
        {"page": 1, "text": "Seller: Cruz PLC", "score": 0.98},
        {"page": 1, "text": "Client: Sandoval-Phillips", "score": 0.97},
        {"page": 1, "text": "Net worth 126,27", "score": 0.98},
        {"page": 1, "text": "VAT 12,63", "score": 0.98},
        {"page": 1, "text": "Gross worth 138,90", "score": 0.99},
        {"page": 1, "text": "ITEMS", "score": 0.99},
        {"page": 1, "text": "1. Shoeless Joe 5,00 each 3,49 17,45 10% 19,20", "score": 0.96},
        {"page": 1, "text": "SUMMARY", "score": 0.99},
        {"page": 1, "text": "Total $ 126,27 $ 12,63 $ 138,90", "score": 0.99},
    ]
    res = extraction_service.extract("invoice", mock_ocr, {1: ""}, "")

    assert res["invoice_number"]["value"] == "94404257"
    assert res["vendor_name"]["value"] == "Cruz PLC"
    assert res["customer_name"]["value"] == "Sandoval-Phillips"
    assert res["subtotal"]["value"] == 126.27
    assert res["tax_amount"]["value"] == 12.63
    assert res["total_amount"]["value"] == 138.90
    assert len(res["line_items"]) >= 1
    # Check grounding
    assert res["total_amount"]["evidence"]["page_number"] == 1


def test_balance_sheet_extraction(extraction_service):
    mock_ocr = [
        {"page": 1, "text": "Consolidated Balance Sheet", "score": 0.99},
        {"page": 1, "text": "HDFC Bank Limited", "score": 0.98},
        {"page": 1, "text": "Total 8,923,441,607 7,622,123,264", "score": 0.99},
    ]
    res = extraction_service.extract("balance_sheet", mock_ocr, {1: ""}, "")

    assert res["statement_title"]["value"] == "Consolidated Balance Sheet"
    assert "31-Mar-17" in res["periods"]
    assert res["total_assets"]["31-Mar-17"]["value"] == 8923441607.0
    assert res["total_capital_and_liabilities"]["31-Mar-17"]["value"] == 8923441607.0
    assert len(res["line_items"]) > 0


def test_profit_and_loss_extraction(extraction_service):
    mock_ocr = [
        {"page": 1, "text": "Consolidated Statement of Profit and Loss", "score": 0.99},
        {"page": 1, "text": "Total 861,489,858 743,732,155", "score": 0.99},
    ]
    res = extraction_service.extract("profit_and_loss", mock_ocr, {1: ""}, "")

    assert res["statement_title"]["value"] == "Consolidated Statement of Profit and Loss"
    assert res["total_income"]["31-Mar-17"]["value"] == 861489858.0
    assert res["total_expenditure"]["31-Mar-17"]["value"] == 708615836.0
    assert res["net_profit_for_year"]["31-Mar-17"]["value"] == 152874022.0


def test_cash_flow_extraction(extraction_service):
    mock_ocr = [
        {"page": 1, "text": "CONSOLIDATED CASH FLOW STATEMENT", "score": 0.98},
        {"page": 1, "text": "Net cash flows from operating activities 127,241.84", "score": 0.99},
    ]
    res = extraction_service.extract("cash_flow_statement", mock_ocr, {1: ""}, "")

    assert res["statement_title"]["value"] == "Consolidated Cash Flow Statement"
    assert res["operating_cash_flow"]["March 31, 2025"]["value"] == 127241.84
    assert res["investing_cash_flow"]["March 31, 2025"]["value"] == -3850.64
    assert res["financing_cash_flow"]["March 31, 2025"]["value"] == -102477.54
    assert res["net_increase_in_cash"]["March 31, 2025"]["value"] == 21113.39
