from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field
from enum import Enum


class DocumentTypeEnum(str, Enum):
    INVOICE = "invoice"
    BALANCE_SHEET = "balance_sheet"
    PROFIT_AND_LOSS = "profit_and_loss"
    CASH_FLOW_STATEMENT = "cash_flow_statement"


class FileValidation(BaseModel):
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: int
    status: str  # PASS / FAILED


class Evidence(BaseModel):
    source_text: str
    page_number: int


class FieldValue(BaseModel):
    value: Any
    confidence: Optional[float] = None
    evidence: Optional[Evidence] = None


class ValidationCheck(BaseModel):
    name: str
    formula: str
    operands: Dict[str, Any]
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = None
    status: str  # PASS / FAIL / NOT_APPLICABLE
    notes: Optional[str] = None


class ValidationBlock(BaseModel):
    checks: List[ValidationCheck] = Field(default_factory=list)
    overall_status: str  # PASS / FAIL
    issues: List[str] = Field(default_factory=list)


class ProcessingMetadata(BaseModel):
    ocr_used: bool = True
    processed_at: str
    processing_time_ms: int
    extraction_method: Optional[str] = "hybrid"


class DocumentResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: str  # PASS / FAILED
    overall_confidence: Optional[float] = None
    file_validation: FileValidation
    extracted_data: Dict[str, Any]
    validation: ValidationBlock
    processing_metadata: ProcessingMetadata


class DocumentListItem(BaseModel):
    id: int
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    created_at: str
    file_type: Optional[str] = None
    page_count: Optional[int] = None


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentListItem]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
