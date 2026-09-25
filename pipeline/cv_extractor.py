import pdfplumber

# Below this many characters, a PDF's native text layer is almost certainly empty or
# near-empty (a scanned image page), so we fall back to OCR instead of feeding the LLM
# a near-blank document.
MIN_NATIVE_TEXT_CHARS = 200

# Render resolution for OCR - higher improves accuracy on small fonts at the cost of speed.
OCR_ZOOM = 2.0


def _extract_native_text(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


def _extract_via_ocr(pdf_path: str) -> str:
    try:
        import pymupdf
        import pytesseract
        from PIL import Image
        import io
    except ImportError as e:
        raise RuntimeError(
            "OCR dependencies missing. Install with: pip install pymupdf pytesseract pillow"
        ) from e

    doc = pymupdf.open(pdf_path)
    text_parts = []
    matrix = pymupdf.Matrix(OCR_ZOOM, OCR_ZOOM)
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            text_parts.append(pytesseract.image_to_string(image))
        except Exception as e:
            raise RuntimeError(
                "OCR failed - is the Tesseract binary installed and on PATH? "
                "Windows: https://github.com/UB-Mannheim/tesseract/wiki | "
                "macOS: brew install tesseract | Linux: apt install tesseract-ocr"
            ) from e
    doc.close()
    return "\n".join(text_parts).strip()


def extract_text(pdf_path: str) -> str:
    """Extract text from a CV PDF, using the native text layer when present and falling
    back to OCR automatically for scanned/image-only PDFs.
    """
    native_text = _extract_native_text(pdf_path)
    if len(native_text) >= MIN_NATIVE_TEXT_CHARS:
        return native_text

    print("[cv_extractor] Little to no embedded text found - this looks like a scanned "
          "PDF. Falling back to OCR...")
    ocr_text = _extract_via_ocr(pdf_path)
    if not ocr_text:
        raise ValueError(
            "Could not extract any text from this PDF, even with OCR. "
            "The file may be corrupted or blank."
        )
    return ocr_text
