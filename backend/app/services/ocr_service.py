import os
import tempfile
from typing import List, Dict, Any, Tuple
import pymupdf
from rapidocr_onnxruntime import RapidOCR
from backend.app.core.logging import logger


class OCRService:
    _instance = None
    _engine = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRService, cls).__new__(cls)
            try:
                cls._engine = RapidOCR()
                logger.info("RapidOCR ONNX engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize RapidOCR engine: {e}")
                cls._engine = None
        return cls._instance

    def extract_text_and_ocr(
        self, file_path: str, filename: str
    ) -> Tuple[List[Dict[str, Any]], Dict[int, str], float, bool]:
        """
        Extracts lines with page number, text, bounding box, and score.
        Returns:
            ocr_lines: List[Dict[str, Any]]
            text_by_page: Dict[int, str]
            average_confidence: float
            ocr_used: bool
        """
        ext = os.path.splitext(filename.lower())[1]
        ocr_lines: List[Dict[str, Any]] = []
        text_by_page: Dict[int, str] = {}
        ocr_used = False

        if ext == ".pdf":
            doc = pymupdf.open(file_path)
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                native_text = page.get_text()

                # If page has substantial native text, use it
                if native_text and len(native_text.strip()) > 100:
                    text_by_page[page_num] = native_text
                    # Split native text into lines for grounding
                    for line in native_text.splitlines():
                        trimmed = line.strip()
                        if trimmed:
                            ocr_lines.append({
                                "page": page_num,
                                "text": trimmed,
                                "score": 0.99,
                                "box": [],
                            })
                else:
                    # Sparse / vector / scanned page: render image and run RapidOCR
                    ocr_used = True
                    pix = page.get_pixmap(dpi=200)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp_path = tmp.name
                    try:
                        pix.save(tmp_path)
                        if self._engine:
                            res, _ = self._engine(tmp_path)
                            page_text_lines = []
                            if res:
                                for bbox, text, score in res:
                                    t = str(text).strip()
                                    if t:
                                        ocr_lines.append({
                                            "page": page_num,
                                            "text": t,
                                            "score": round(float(score), 4),
                                            "box": bbox,
                                        })
                                        page_text_lines.append(t)
                            text_by_page[page_num] = "\n".join(page_text_lines)
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
            doc.close()

        elif ext in (".jpg", ".jpeg", ".png"):
            ocr_used = True
            if self._engine:
                res, _ = self._engine(file_path)
                page_text_lines = []
                if res:
                    for bbox, text, score in res:
                        t = str(text).strip()
                        if t:
                            ocr_lines.append({
                                "page": 1,
                                "text": t,
                                "score": round(float(score), 4),
                                "box": bbox,
                            })
                            page_text_lines.append(t)
                text_by_page[1] = "\n".join(page_text_lines)

        # Compute average confidence
        if ocr_lines:
            scores = [item["score"] for item in ocr_lines if item.get("score") is not None]
            avg_confidence = round(sum(scores) / len(scores), 4) if scores else 0.95
        else:
            avg_confidence = 0.0

        logger.info(
            f"OCR finished for '{filename}': extracted {len(ocr_lines)} lines, avg confidence {avg_confidence:.4f}, ocr_used={ocr_used}"
        )
        return ocr_lines, text_by_page, avg_confidence, ocr_used
