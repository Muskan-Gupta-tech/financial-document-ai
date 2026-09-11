from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from backend.app.core.database import Base


class ProcessedDocument(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_name = Column(String(255), index=True, nullable=False)
    document_type = Column(String(50), index=True, nullable=False)
    processing_status = Column(String(20), index=True, nullable=False)  # PASS / FAILED
    overall_confidence = Column(Float, nullable=True)

    file_validation = Column(JSON, nullable=False, default=dict)
    extracted_data = Column(JSON, nullable=False, default=dict)
    validation_results = Column(JSON, nullable=False, default=dict)
    processing_metadata = Column(JSON, nullable=False, default=dict)

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "processing_status": self.processing_status,
            "overall_confidence": self.overall_confidence,
            "file_validation": self.file_validation,
            "extracted_data": self.extracted_data,
            "validation": self.validation_results,
            "processing_metadata": self.processing_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
