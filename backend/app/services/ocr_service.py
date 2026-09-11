import os
import gc
import tempfile
from typing import List, Dict, Any, Tuple
import pymupdf
from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from backend.app.core.logging import logger

# Longest side (px) an image is allowed to reach before OCR runs on it.
# RapidOCR/ONNX memory scales with pixel count, and uploaded JPG/PNGs
# (e.g. phone photos) can be 3000-4000px+ on the long side, which is
# almost certainly what pushes the Render free instance (512MB) over
# its limit. 2000px keeps text legible for typical financial documents
# while cutting worst-case pixel count (and OCR memory) by 4x or more.
# Override via env var if a case ever needs a different ceiling.
MAX_OCR_DIMENSION = int(os.environ.get("OCR_MAX_DIMENSION", "2000"))

# Default render DPI for PDF pages that need OCR (unchanged default
# behavior). Kept as a constant so it can be scaled down per-page below
# instead of hardcoded inline.
PDF_RENDER_DPI = int(os.environ.get("OCR_PDF_DPI", "200"))


class OCRService:
    _instance = None
    _engine = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRService, cls).__new__(cls)
            try:
                # Singleton engine preserved as-is: RapidOCR/ONNX model
                # weights are loaded once per process, never per-request.
                cls._engine = RapidOCR()
                logger.info("RapidOCR ONNX engine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize RapidOCR engine: {e}")
                cls._engine = None
        return cls._instance

    @staticmethod
    def _downscale_image_if_needed(source_path: str) -> Tuple[str, bool]:
        """
        Inspects an image's dimensions and, if it exceeds MAX_OCR_DIMENSION
        on its longest side, writes a downscaled copy to a temp file for
        OCR to run against. Aspect ratio is preserved via PIL's thumbnail().

        Returns (path_to_use_for_ocr, is_temp_file_that_needs_cleanup).
        Normal-sized documents are returned unchanged (no resize, no copy),
        so accuracy on typical scans/invoices is not affected.
        """
        with Image.open(source_path) as img:
            width, height = img.size
            if max(width, height) <= MAX_OCR_DIMENSION:
                # Already within budget - use original, no extra copy in memory.
                return source_path, False

            # Downscale preserving aspect ratio; thumbnail() mutates in place
            # on a single decoded copy rather than allocating a second
            # full-resolution buffer.
            img.thumbnail((MAX_OCR_DIMENSION, MAX_OCR_DIMENSION), Image.LANCZOS)
            fd, resized_path = tempfile.mkstemp(suffix=os.path.splitext(source_path)[1] or ".png")
            os.close(fd)
            img.save(resized_path)
            logger.info(
                f"Downscaled image from {width}x{height} to max {MAX_OCR_DIMENSION}px "
                f"before OCR to reduce memory usage."
            )
        return resized_path, True

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
            try:
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

                        # Cap the rendered pixel size to MAX_OCR_DIMENSION by
                        # scaling the DPI down for unusually large page
                        # dimensions, instead of always rendering at a fixed
                        # 200 DPI regardless of page size.
                        rect = page.rect
                        dpi = PDF_RENDER_DPI
                        projected_max_px = max(rect.width, rect.height) / 72 * dpi
                        if projected_max_px > MAX_OCR_DIMENSION:
                            dpi = max(72, int(dpi * (MAX_OCR_DIMENSION / projected_max_px)))

                        pix = page.get_pixmap(dpi=dpi)
                        tmp_path = None
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                                tmp_path = tmp.name
                            pix.save(tmp_path)
                            # Release the rendered pixmap buffer immediately -
                            # it's no longer needed once written to disk, and
                            # holding it for the rest of the loop iteration
                            # keeps a full-resolution page image alive
                            # alongside the next page's buffer.
                            del pix
                            gc.collect()

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
                            if tmp_path and os.path.exists(tmp_path):
                                os.remove(tmp_path)
            finally:
                doc.close()

        elif ext in (".jpg", ".jpeg", ".png"):
            ocr_used = True
            if self._engine:
                # Previously the original upload was fed straight into
                # RapidOCR with no size check. Large photos (phone camera
                # JPGs are commonly 3000-4000px+ on a side) are the most
                # likely cause of the Render OOM on JPG uploads - this is
                # the key fix for that failure mode.
                ocr_path, is_temp = self._downscale_image_if_needed(file_path)
                try:
                    res, _ = self._engine(ocr_path)
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
                finally:
                    # Only clean up if we created a resized copy - never
                    # touch the caller's original uploaded file.
                    if is_temp and os.path.exists(ocr_path):
                        os.remove(ocr_path)

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