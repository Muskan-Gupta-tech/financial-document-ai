import os
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentListItem,
    DocumentTypeEnum,
)
from backend.app.services.document_service import DocumentService
from backend.app.services.document_validation_service import DocumentValidationException
from backend.app.repositories.document_repository import DocumentRepository
from backend.app.core.logging import logger

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/process",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and process a financial document",
)
async def process_document_endpoint(
    file: UploadFile = File(..., description="PDF / JPG / PNG document to extract and validate"),
    document_type: str = Form(
        ...,
        description="Document type: invoice | balance_sheet | profit_and_loss | cash_flow_statement",
    ),
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/documents/process
    Accepts multipart/form-data with file and document_type.
    Validates document, runs OCR/extraction, performs financial calculations, stores result, and returns JSON.
    """
    # 1. Validate document_type parameter
    doc_type_clean = document_type.lower().strip()
    valid_types = [t.value for t in DocumentTypeEnum]
    if doc_type_clean not in valid_types:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "INVALID_DOCUMENT_TYPE",
                    "message": f"Invalid document_type '{document_type}'. Supported types: {', '.join(valid_types)}",
                }
            },
        )

    # 2. Save file temporarily
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_filename = os.path.basename(file.filename or "upload.pdf")
    dest_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to write uploaded file '{safe_filename}': {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "FILE_SAVE_ERROR",
                    "message": "Failed to store uploaded file on server.",
                }
            },
        )

    # 3. Process Document
    try:
        service = DocumentService(db)
        response: DocumentResponse = service.process_document(
            file_path=dest_path,
            filename=safe_filename,
            document_type=doc_type_clean,
        )
        return response
    except DocumentValidationException as dve:
        return JSONResponse(
            status_code=dve.status_code,
            content={"error": {"code": dve.code, "message": dve.message}},
        )
    except Exception as e:
        logger.exception(f"Unexpected error while processing '{safe_filename}': {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "PROCESSING_ERROR",
                    "message": f"Internal document processing error: {str(e)}",
                }
            },
        )


@router.get(
    "/{document_name}",
    response_model=DocumentResponse,
    summary="Retrieve latest structured result for a document",
)
def get_document_by_name(document_name: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/documents/{document_name}
    Returns the latest structured extraction result for the specified document name.
    """
    repo = DocumentRepository(db)
    doc = repo.get_latest_by_name(document_name)
    if not doc:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document '{document_name}' has not been processed or was not found.",
                }
            },
        )

    return DocumentResponse(
        document_name=doc.document_name,
        document_type=doc.document_type,
        processing_status=doc.processing_status,
        overall_confidence=doc.overall_confidence,
        file_validation=doc.file_validation,
        extracted_data=doc.extracted_data,
        validation=doc.validation_results,
        processing_metadata=doc.processing_metadata,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all processed documents",
)
def list_documents(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/documents
    Lists processed documents for the dashboard.
    """
    repo = DocumentRepository(db)
    docs = repo.list_documents(limit=limit, offset=offset)
    total = repo.count_documents()

    items = []
    for d in docs:
        file_val = d.file_validation or {}
        items.append(
            DocumentListItem(
                id=d.id,
                document_name=d.document_name,
                document_type=d.document_type,
                processing_status=d.processing_status,
                overall_confidence=d.overall_confidence,
                created_at=d.created_at.isoformat() if d.created_at else "",
                file_type=file_val.get("file_type"),
                page_count=file_val.get("page_count"),
            )
        )

    return DocumentListResponse(total=total, documents=items)
