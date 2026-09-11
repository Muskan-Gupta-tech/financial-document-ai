import os
import tempfile
import pytest
import pymupdf
from PIL import Image
from backend.app.services.document_validation_service import (
    DocumentValidationService,
    DocumentValidationException,
)
from backend.app.services.financial_validation_service import FinancialValidationService


# ==========================================
# 1. Document Input Validation Tests
# ==========================================
def test_valid_image_file():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(tmp.name)
        tmp_path = tmp.name

    try:
        val = DocumentValidationService.validate_file(tmp_path, "test_image.jpg")
        assert val.status == "PASS"
        assert val.is_supported is True
        assert val.page_count == 1
        assert val.file_type == "image/jpeg"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_empty_file_rejection():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        with pytest.raises(DocumentValidationException) as exc_info:
            DocumentValidationService.validate_file(tmp_path, "empty.pdf")
        assert exc_info.value.code == "CORRUPTED_OR_EMPTY_FILE"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_unsupported_file_extension():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"Hello world")
        tmp_path = tmp.name

    try:
        with pytest.raises(DocumentValidationException) as exc_info:
            DocumentValidationService.validate_file(tmp_path, "document.txt")
        assert exc_info.value.code == "UNSUPPORTED_FILE_TYPE"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_pdf_page_limit_exceeded():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    # Create a 4-page PDF
    doc = pymupdf.open()
    for _ in range(4):
        doc.new_page()
    doc.save(tmp_path)
    doc.close()

    try:
        with pytest.raises(DocumentValidationException) as exc_info:
            DocumentValidationService.validate_file(tmp_path, "multi_page.pdf")
        assert exc_info.value.code == "PAGE_LIMIT_EXCEEDED"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ==========================================
# 2. Financial Validation Calculation Tests
# ==========================================
def test_invoice_financial_validation_success():
    service = FinancialValidationService(tolerance=0.05)
    mock_invoice = {
        "subtotal": {"value": 30.92},
        "tax_amount": {"value": 3.09},
        "discount": {"value": 0.0},
        "total_amount": {"value": 34.01},
        "line_items": [
            {"item_number": 1, "quantity": 5.0, "unit_price": 3.49, "amount": 17.45},
            {"item_number": 2, "quantity": 3.0, "unit_price": 4.49, "amount": 13.47},
        ],
    }
    result = service.validate("invoice", mock_invoice)
    assert result.overall_status == "PASS"
    assert len(result.issues) == 0

    # Total check verification
    tot_chk = next(c for c in result.checks if c.name == "invoice_total_check")
    assert tot_chk.status == "PASS"
    assert tot_chk.calculated_value == 34.01
    assert tot_chk.variance == 0.0


def test_invoice_financial_validation_failure():
    service = FinancialValidationService(tolerance=0.05)
    mock_bad_invoice = {
        "subtotal": {"value": 100.00},
        "tax_amount": {"value": 10.00},
        "discount": {"value": 0.0},
        "total_amount": {"value": 200.00},  # Intentionally wrong total!
        "line_items": [
            {"item_number": 1, "quantity": 2.0, "unit_price": 50.0, "amount": 100.00}
        ],
    }
    result = service.validate("invoice", mock_bad_invoice)
    assert result.overall_status == "FAIL"
    assert len(result.issues) > 0

    tot_chk = next(c for c in result.checks if c.name == "invoice_total_check")
    assert tot_chk.status == "FAIL"
    assert tot_chk.variance == 90.00


def test_balance_sheet_equation_validation():
    service = FinancialValidationService(tolerance=1.0)
    mock_bs = {
        "periods": ["31-Mar-17"],
        "total_capital_and_liabilities": {"31-Mar-17": {"value": 8923441607.0}},
        "total_assets": {"31-Mar-17": {"value": 8923441607.0}},
        "line_items": [
            {"category": "capital_and_liabilities", "item_name": "Capital", "values_by_period": {"31-Mar-17": 5125091.0}},
            {"category": "capital_and_liabilities", "item_name": "Reserves", "values_by_period": {"31-Mar-17": 8918316516.0}},
            {"category": "assets", "item_name": "Advances", "values_by_period": {"31-Mar-17": 8923441607.0}},
        ],
    }
    result = service.validate("balance_sheet", mock_bs)
    assert result.overall_status == "PASS"
    eq_chk = next(c for c in result.checks if "balance_sheet_equation" in c.name)
    assert eq_chk.status == "PASS"
    assert eq_chk.variance == 0.0


def test_cash_flow_parentheses_and_reconciliation():
    service = FinancialValidationService(tolerance=1.0)
    mock_cf = {
        "periods": ["March 31, 2025"],
        "operating_cash_flow": {"March 31, 2025": {"value": 127241.84}},
        "investing_cash_flow": {"March 31, 2025": {"value": -3850.64}},
        "financing_cash_flow": {"March 31, 2025": {"value": -102477.54}},
        "fx_translation_adjustment": {"March 31, 2025": {"value": 199.73}},
        "net_increase_in_cash": {"March 31, 2025": {"value": 21113.39}},
        "opening_cash": {"March 31, 2025": {"value": 228834.51}},
        "amalgamation_cash": {"March 31, 2025": {"value": 0.0}},
        "closing_cash": {"March 31, 2025": {"value": 249947.90}},
    }
    result = service.validate("cash_flow_statement", mock_cf)
    assert result.overall_status == "PASS"

    net_chk = next(c for c in result.checks if "net_cash_flow_reconciliation" in c.name)
    assert net_chk.status == "PASS"
    assert net_chk.calculated_value == 21113.39

    close_chk = next(c for c in result.checks if "closing_cash_reconciliation" in c.name)
    assert close_chk.status == "PASS"
    assert close_chk.calculated_value == 249947.90
