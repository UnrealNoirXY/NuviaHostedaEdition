import base64
import binascii
import io
import logging
import re
from datetime import datetime
from typing import Dict, Tuple

import cv2
import numpy as np
from PIL import Image
import pytesseract


logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_FORMATS = {"JPEG", "PNG", "JPG"}
MIN_OCR_SIDE_PX = 1024


def _clean_base64(data: str) -> bytes:
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Immagine non valida") from exc


def load_image_from_payload(*, image_file=None, image_base64: str = None) -> Image.Image:
    """Decodifica un'immagine proveniente dal payload.

    L'immagine può essere fornita come file (multipart) o come stringa base64.
    Viene applicato un limite di dimensione e una validazione basilare del formato.
    """

    if not image_file and not image_base64:
        raise ValueError("Nessuna immagine fornita")

    if image_base64:
        raw_bytes = _clean_base64(image_base64)
    else:
        raw_bytes = image_file.read()

    if len(raw_bytes) > MAX_IMAGE_SIZE:
        raise ValueError("L'immagine supera il limite di 5MB")

    try:
        image = Image.open(io.BytesIO(raw_bytes))
    except Exception as exc:  # pragma: no cover - handled by raising ValueError
        raise ValueError("Immagine non valida") from exc

    image_format = (image.format or "").upper()
    if image_format and image_format not in ALLOWED_FORMATS:
        raise ValueError("Formato immagine non supportato. Usa PNG o JPEG")

    return image.convert("RGB")


def _normalize_date(raw: str) -> str:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def extract_fields_from_text(text: str) -> Dict[str, str]:
    """Ritorna un dizionario con i campi principali estratti dal testo OCR."""

    normalized = text.replace("\n", " \n ")
    date_match = re.search(r"(\d{2}[\/\.-]\d{2}[\/\.-]\d{4}|\d{4}-\d{2}-\d{2})", normalized)
    doc_match = re.search(r"([A-Z0-9]{5,})", normalized, re.IGNORECASE)

    names: Tuple[str, str] = ("", "")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", lines[0])
        if len(tokens) >= 2:
            names = (tokens[0].title(), " ".join(tokens[1:]).title())

    return {
        "first_name": names[0],
        "last_name": names[1],
        "document_number": doc_match.group(1).upper() if doc_match else "",
        "document_expiry_date": _normalize_date(date_match.group(1)) if date_match else "",
    }


def perform_ocr(image: Image.Image) -> Dict[str, object]:
    """Esegue l'OCR e ritorna i campi più rilevanti più un punteggio di confidenza."""
    preprocessed = _preprocess_document(image)

    ocr_text = pytesseract.image_to_string(preprocessed)
    data = pytesseract.image_to_data(preprocessed, output_type=pytesseract.Output.DICT)
    confidences = [float(c) for c in data.get("conf", []) if str(c).strip().isdigit()]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    fields = extract_fields_from_text(ocr_text)
    return {"fields": fields, "confidence": round(avg_conf / 100, 3)}


def _pil_to_cv(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def _cv_to_pil(image: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def _largest_quad(contours):
    max_area = 0
    best = None
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area > max_area:
                max_area = area
                best = approx
    return best


def _order_points(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2)
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def _detect_and_crop_document(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    v = float(np.median(blurred))
    lower = int(max(0, (1.0 - 0.33) * v))
    upper = int(min(255, (1.0 + 0.33) * v))
    edges = cv2.Canny(blurred, lower, upper)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    quad = _largest_quad(contours)
    if quad is None:
        return image

    rect = _order_points(quad)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))

    if maxWidth < 100 or maxHeight < 100:
        return image

    dst = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped


def _deskew(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle

    if abs(angle) < 0.5:
        return image

    (h, w) = image.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated


def _white_balance(image: np.ndarray) -> np.ndarray:
    result = image.astype(np.float32)
    avg = result.reshape(-1, 3).mean(axis=0)
    scale = avg.mean() / (avg + 1e-6)
    balanced = np.clip(result * scale, 0, 255).astype(np.uint8)
    return balanced


def _denoise(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)


def _resize_min_side(image: np.ndarray, min_side: int = MIN_OCR_SIDE_PX) -> np.ndarray:
    h, w = image.shape[:2]
    current_min = min(h, w)
    if current_min >= min_side:
        return image
    scale = min_side / float(current_min)
    new_size = (int(w * scale), int(h * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)


def _validate_orientation(image: Image.Image) -> Image.Image:
    try:
        osd = pytesseract.image_to_osd(image)
        rotation_match = re.search(r"Rotate:\s(\d+)", osd)
        if rotation_match:
            angle = int(rotation_match.group(1)) % 360
            if angle != 0:
                return image.rotate(-angle, expand=True)
    except pytesseract.TesseractError:
        return image
    except Exception:
        logger.exception("Errore durante la validazione dell'orientamento")
        return image
    return image


def _preprocess_document(image: Image.Image) -> Image.Image:
    cv_image = _pil_to_cv(image)

    cropped = _detect_and_crop_document(cv_image)
    deskewed = _deskew(cropped)
    balanced = _white_balance(deskewed)
    denoised = _denoise(balanced)
    resized = _resize_min_side(denoised)

    pil_image = _cv_to_pil(resized)
    validated = _validate_orientation(pil_image)

    width, height = validated.size
    if min(width, height) < MIN_OCR_SIDE_PX * 0.5:
        raise ValueError("L'immagine è troppo piccola per un OCR affidabile")

    return validated
