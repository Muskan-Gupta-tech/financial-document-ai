from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models.document import ProcessedDocument


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, doc: ProcessedDocument) -> ProcessedDocument:
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_latest_by_name(self, document_name: str) -> Optional[ProcessedDocument]:
        return (
            self.db.query(ProcessedDocument)
            .filter(ProcessedDocument.document_name == document_name)
            .order_by(desc(ProcessedDocument.id))
            .first()
        )

    def get_by_id(self, doc_id: int) -> Optional[ProcessedDocument]:
        return self.db.query(ProcessedDocument).filter(ProcessedDocument.id == doc_id).first()

    def list_documents(self, limit: int = 100, offset: int = 0) -> List[ProcessedDocument]:
        return (
            self.db.query(ProcessedDocument)
            .order_by(desc(ProcessedDocument.id))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_documents(self) -> int:
        return self.db.query(ProcessedDocument).count()
