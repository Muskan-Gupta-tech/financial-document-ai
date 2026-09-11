import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.schemas.document import (
    DocumentResponse,
    FileValidation,
    ValidationBlock,
    ProcessingMetadata,
)
from backend.app.models.document import ProcessedDocument
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.services.document_validation_service import (
    DocumentValidationService,
    DocumentValidationException,
)
from backend.app.services.ocr_service import OCRService
from backend.app.services.extraction_service import ExtractionService
from backend.app.services.financial_validation_service import FinancialValidationService
from backend.app.core.logging import logger


class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)
        self.validation_service = DocumentValidationService()
        self.ocr_service = OCRService()
        self.extraction_service = ExtractionService()
        self.financial_validation_service = FinancialValidationService()

    def process_document(
        self,
        file_path: str,
        filename: str,
        document_type: str,
    ) -> DocumentResponse:
        start_time = time.time()
        logger.info(f"Starting processing for '{filename}' with type '{document_type}'")

        # 1. Document Validation Layer
        file_val: FileValidation = self.validation_service.validate_file(file_path, filename)

        # 2. Text Extraction & OCR
        ocr_lines, text_by_page, avg_ocr_confidence, ocr_used = (
            self.ocr_service.extract_text_and_ocr(file_path, filename)
        )
        full_text = "\n\n".join(text_by_page.values())

        # 3. AI / Structured Extraction
        extracted_data = self.extraction_service.extract(
            document_type=document_type,
            ocr_lines=ocr_lines,
            text_by_page=text_by_page,
            full_text=full_text,
        )

        # 4. Financial Calculation Validation
        validation_result: ValidationBlock = self.financial_validation_service.validate(
            document_type=document_type,
            extracted_data=extracted_data,
        )

        # 5. Determine Overall Processing Status (PASS / FAILED)
        # PASS if file is valid and all required financial calculations pass
        processing_status = "PASS" if validation_result.overall_status == "PASS" else "FAILED"

        # 6. Compute Overall Confidence
        field_confidences = []
        for k, v in extracted_data.items():
            if isinstance(v, dict) and "confidence" in v and v["confidence"] is not None:
                field_confidences.append(float(v["confidence"]))

        if field_confidences:
            overall_conf = round(sum(field_confidences) / len(field_confidences), 2)
        elif avg_ocr_confidence > 0:
            overall_conf = round(avg_ocr_confidence, 2)
        else:
            overall_conf = 0.95

        elapsed_ms = int((time.time() - start_time) * 1000)
        proc_metadata = ProcessingMetadata(
            ocr_used=ocr_used,
            processed_at=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=elapsed_ms,
            extraction_method="llm" if self.extraction_service.gemini_client else "deterministic_parser",
        )

        response = DocumentResponse(
            document_name=filename,
            document_type=document_type,
            processing_status=processing_status,
            overall_confidence=overall_conf,
            file_validation=file_val,
            extracted_data=extracted_data,
            validation=validation_result,
            processing_metadata=proc_metadata,
        )

        # 7. Persist to Database
        db_doc = ProcessedDocument(
            document_name=filename,
            document_type=document_type,
            processing_status=processing_status,
            overall_confidence=overall_conf,
            file_validation=file_val.model_dump(),
            extracted_data=extracted_data,
            validation_results=validation_result.model_dump(),
            processing_metadata=proc_metadata.model_dump(),
        )
        self.repo.save(db_doc)
        logger.info(
            f"Successfully processed and stored '{filename}'. Status: {processing_status}, Time: {elapsed_ms}ms"
        )
        return response
