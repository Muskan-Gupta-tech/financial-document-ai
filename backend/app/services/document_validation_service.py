import os
from typing import Tuple
import pymupdf
from PIL import Image
from backend.app.core.config import settings
from backend.app.schemas.document import FileValidation
from backend.app.core.logging import logger


class DocumentValidationException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DocumentValidationService:
    @staticmethod
    def validate_file(file_path: str, filename: str) -> FileValidation:
        """
        Validates file integrity, format, readability, and page count <= 3.
        Raises DocumentValidationException if invalid.
        """
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            logger.warning(f"File validation failed: empty or nonexistent file '{filename}'")
            raise DocumentValidationException(
                code="CORRUPTED_OR_EMPTY_FILE",
                message="File is empty or corrupted.",
                status_code=400,
            )

        # Check extension
        ext = os.path.splitext(filename.lower())[1]
        if ext not in settings.ALLOWED_EXTENSIONS:
            logger.warning(f"File validation failed: unsupported extension '{ext}' for file '{filename}'")
            raise DocumentValidationException(
                code="UNSUPPORTED_FILE_TYPE",
                message="Only PDF / JPG / PNG documents are supported.",
                status_code=400,
            )

        page_count = 1
        is_readable = False
        detected_mime = "application/octet-stream"

        if ext == ".pdf":
            detected_mime = "application/pdf"
            try:
                doc = pymupdf.open(file_path)
                page_count = len(doc)
                if page_count == 0:
                    raise ValueError("PDF has 0 pages")
                # Test reading first page
                _ = doc[0].get_pixmap()
                is_readable = True
                doc.close()
            except Exception as e:
                logger.error(f"Failed to read PDF '{filename}': {str(e)}")
                raise DocumentValidationException(
                    code="CORRUPTED_OR_EMPTY_FILE",
                    message="The uploaded PDF file is corrupted or unreadable.",
                    status_code=400,
                )
        elif ext in (".jpg", ".jpeg"):
            detected_mime = "image/jpeg"
            try:
                with Image.open(file_path) as img:
                    img.verify()
                is_readable = True
                page_count = 1
            except Exception as e:
                logger.error(f"Failed to read JPEG image '{filename}': {str(e)}")
                raise DocumentValidationException(
                    code="CORRUPTED_OR_EMPTY_FILE",
                    message="The uploaded JPEG image is corrupted or unreadable.",
                    status_code=400,
                )
        elif ext == ".png":
            detected_mime = "image/png"
            try:
                with Image.open(file_path) as img:
                    img.verify()
                is_readable = True
                page_count = 1
            except Exception as e:
                logger.error(f"Failed to read PNG image '{filename}': {str(e)}")
                raise DocumentValidationException(
                    code="CORRUPTED_OR_EMPTY_FILE",
                    message="The uploaded PNG image is corrupted or unreadable.",
                    status_code=400,
                )

        # Validate page count rule: <= 3 pages
        if page_count > settings.MAX_PAGE_LIMIT:
            logger.warning(
                f"Page count limit exceeded for '{filename}': {page_count} > {settings.MAX_PAGE_LIMIT}"
            )
            raise DocumentValidationException(
                code="PAGE_LIMIT_EXCEEDED",
                message=f"Document exceeds maximum page limit of {settings.MAX_PAGE_LIMIT} pages (found {page_count} pages).",
                status_code=400,
            )

        logger.info(
            f"File validation passed for '{filename}': mime={detected_mime}, pages={page_count}"
        )
        return FileValidation(
            file_type=detected_mime,
            is_supported=True,
            is_readable=is_readable,
            page_count=page_count,
            status="PASS",
        )
