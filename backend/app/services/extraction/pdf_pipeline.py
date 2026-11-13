import os
import shutil
from typing import Dict, List, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None


def is_tesseract_available() -> bool:
    """Checks whether the Tesseract OCR binary is installed and executable."""
    return shutil.which("tesseract") is not None


def extract_pdf_pages_and_thumbnails(
    pdf_path: str,
    output_thumbnail_dir: str,
    doc_id: str,
    min_text_threshold: int = 50,
) -> Dict[str, Any]:
    """
    Extracts high-fidelity word-level text coordinates and generates page thumbnails.
    Routes pages with < min_text_threshold characters to OCR.
    If Tesseract is unavailable, falls back gracefully to PyMuPDF raw text with a transparent flag.
    """
    os.makedirs(output_thumbnail_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    pages_data: List[Dict[str, Any]] = []
    full_text_list: List[str] = []
    ocr_triggered = False

    tesseract_available = is_tesseract_available()

    for page_idx in range(page_count):
        page = doc[page_idx]
        page_num = page_idx + 1
        rect = page.rect
        width = float(rect.width)
        height = float(rect.height)

        # 1. Render and save page thumbnail (PNG)
        pix = page.get_pixmap(dpi=150)
        thumb_filename = f"{doc_id}_p{page_num}.png"
        thumb_path = os.path.join(output_thumbnail_dir, thumb_filename)
        pix.save(thumb_path)

        # 2. Extract word-level bounding boxes via PyMuPDF text layer
        # get_text("words") returns tuples: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        raw_words = page.get_text("words")
        page_text = page.get_text("text").strip()

        word_boxes: List[Dict[str, Any]] = []
        for w in raw_words:
            x0, y0, x1, y1, word_str = w[0], w[1], w[2], w[3], w[4]
            # Normalize to 0.0 - 1.0 range
            norm_bbox = [
                round(x0 / width, 4) if width > 0 else 0.0,
                round(y0 / height, 4) if height > 0 else 0.0,
                round(x1 / width, 4) if width > 0 else 0.0,
                round(y1 / height, 4) if height > 0 else 0.0,
            ]
            word_boxes.append({
                "text": word_str,
                "bbox": norm_bbox,
                "confidence": 0.98,
            })

        method_used = "text_layer"

        # 3. Check for low-text page: route to OCR if < min_text_threshold chars
        if len(page_text) < min_text_threshold:
            ocr_triggered = True
            if tesseract_available and pytesseract:
                try:
                    img = Image.open(thumb_path)
                    # Get word bounding boxes from Tesseract
                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    img_w, img_h = img.size
                    ocr_words = []
                    ocr_text_parts = []
                    n_boxes = len(ocr_data['text'])
                    for i in range(n_boxes):
                        t_word = ocr_data['text'][i].strip()
                        conf = float(ocr_data['conf'][i])
                        if t_word and conf > 20:
                            ocr_text_parts.append(t_word)
                            nx0 = round(ocr_data['left'][i] / img_w, 4)
                            ny0 = round(ocr_data['top'][i] / img_h, 4)
                            nx1 = round((ocr_data['left'][i] + ocr_data['width'][i]) / img_w, 4)
                            ny1 = round((ocr_data['top'][i] + ocr_data['height'][i]) / img_h, 4)
                            ocr_words.append({
                                "text": t_word,
                                "bbox": [nx0, ny0, nx1, ny1],
                                "confidence": round(conf / 100.0, 2),
                            })
                    if ocr_words:
                        word_boxes = ocr_words
                        page_text = " ".join(ocr_text_parts)
                        method_used = "ocr"
                except Exception:
                    method_used = "text_layer_fallback"
            else:
                method_used = "text_layer_fallback"

        full_text_list.append(page_text)
        pages_data.append({
            "page_number": page_num,
            "width": width,
            "height": height,
            "text": page_text,
            "extractor": method_used,
            "word_boxes": word_boxes,
            "thumbnail_filename": thumb_filename,
        })

    doc.close()
    return {
        "page_count": page_count,
        "pages": pages_data,
        "full_text": "\n\n".join(full_text_list),
        "ocr_triggered": ocr_triggered,
        "tesseract_available": tesseract_available,
    }


def extract_image_page(
    image_path: str,
    output_thumbnail_dir: str,
    doc_id: str,
) -> Dict[str, Any]:
    """
    Handles image uploads (JPG/PNG). Creates thumbnail and runs OCR or returns fallback structure.
    """
    os.makedirs(output_thumbnail_dir, exist_ok=True)
    img = Image.open(image_path)
    img_w, img_h = img.size

    thumb_filename = f"{doc_id}_p1.png"
    thumb_path = os.path.join(output_thumbnail_dir, thumb_filename)
    img.save(thumb_path)

    tesseract_available = is_tesseract_available()
    word_boxes: List[Dict[str, Any]] = []
    text_content = ""
    extractor = "ocr" if tesseract_available else "text_layer_fallback"

    if tesseract_available and pytesseract:
        try:
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n_boxes = len(ocr_data['text'])
            text_parts = []
            for i in range(n_boxes):
                t_word = ocr_data['text'][i].strip()
                conf = float(ocr_data['conf'][i])
                if t_word and conf > 20:
                    text_parts.append(t_word)
                    word_boxes.append({
                        "text": t_word,
                        "bbox": [
                            round(ocr_data['left'][i] / img_w, 4),
                            round(ocr_data['top'][i] / img_h, 4),
                            round((ocr_data['left'][i] + ocr_data['width'][i]) / img_w, 4),
                            round((ocr_data['top'][i] + ocr_data['height'][i]) / img_h, 4),
                        ],
                        "confidence": round(conf / 100.0, 2),
                    })
            text_content = " ".join(text_parts)
        except Exception:
            extractor = "text_layer_fallback"

    return {
        "page_count": 1,
        "pages": [{
            "page_number": 1,
            "width": float(img_w),
            "height": float(img_h),
            "text": text_content,
            "extractor": extractor,
            "word_boxes": word_boxes,
            "thumbnail_filename": thumb_filename,
        }],
        "full_text": text_content,
        "ocr_triggered": True,
        "tesseract_available": tesseract_available,
    }
