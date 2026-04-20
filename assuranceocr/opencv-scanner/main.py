import os
import base64
import logging
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn
# ==========================================
# SETUP & CONFIG
# ==========================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OnWave Scanner — OpenCV Optimizer API",
    description=(
        "Accepts PDF + Image (or both), rasterizes at 300 DPI, "
        "and returns optimized base64 images ready for GPT Vision in n8n."
    ),
    version="3.0.0"
)

# Global reference for lazy loading
_yolo_model = None
SMART_MERGE_GAP_THRESHOLD = 50


def get_yolo_models():
    """Lazy-load custom YOLO models. Returns list of (model, name, type) tuples.
    Types: 'obb' (oriented bounding box) or 'classic' (axis-aligned).
    OBB models run first for document-type identification priority.
    """
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            models = []
            # OBB model first (document-type identifier, takes priority)
            if os.path.exists("best2.pt"):
                logger.info("Loading YOLO-OBB model: best2.pt")
                models.append((YOLO("best2.pt"), "best2.pt", "obb"))
            # Classic models (card/document detectors)
            # if os.path.exists("best.pt"):
            #     logger.info("Loading YOLO-Classic model: best.pt")
            #     models.append((YOLO("best.pt"), "best.pt", "classic"))
            if os.path.exists("best1.pt"):
                logger.info("Loading YOLO-Classic model: best1.pt")
                models.append((YOLO("best1.pt"), "best1.pt", "classic"))
            if os.path.exists("best_a4.pt"):
                logger.info("Loading YOLO-Classic model: best_a4.pt")
                models.append((YOLO("best_a4.pt"), "best_a4.pt", "classic"))
            
            if not models:
                logger.warning("No custom YOLO models found. OpenCV fallback will be used.")
                
            _yolo_model = models
            logger.info(f"{len(models)} YOLO model(s) loaded successfully")
        except Exception as e:
            logger.warning(f"YOLO model loading failed: {e}")
            return []
    return _yolo_model



# ==========================================
# STEP 2: THE CRACKER — PyMuPDF Module
# ==========================================
def crack_pdf(file_bytes: bytes) -> List[np.ndarray]:
    """Rasterizes every PDF page at 300 DPI for maximum OCR precision."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    zoom = 300 / 72.0  # 300 DPI: high quality for sharp text extraction
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        images.append(bgr)
        logger.info(f"PDF page {i+1}/{len(doc)} → {pix.width}x{pix.height}px @ 300 DPI")
    doc.close()
    return images


def crack_image(file_bytes: bytes) -> np.ndarray:
    """Decodes a raw image file (JPG/PNG) into an OpenCV BGR array."""
    nparr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image — invalid bytes or unsupported format")
    return img


def _clip_xyxy_box(box: Tuple[int, int, int, int], w: int, h: int) -> Tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid crop box after clipping: {box}")
    return x1, y1, x2, y2


def _extract_boxes_xyxy(yolo_results: Any) -> List[Tuple[int, int, int, int]]:
    """
    Extract xyxy boxes from Ultralytics YOLO results.
    Supports a Results object, a list of Results, or direct box arrays.
    """
    result_items = yolo_results if isinstance(yolo_results, (list, tuple)) else [yolo_results]
    boxes: List[Tuple[int, int, int, int]] = []

    for item in result_items:
        if hasattr(item, "boxes") and item.boxes is not None and hasattr(item.boxes, "xyxy"):
            xyxy = item.boxes.xyxy
            xyxy = xyxy.cpu().numpy() if hasattr(xyxy, "cpu") else np.asarray(xyxy)
        else:
            xyxy = np.asarray(item)
            if xyxy.ndim != 2 or xyxy.shape[1] < 4:
                continue

        for b in xyxy:
            x1, y1, x2, y2 = map(int, b[:4])
            boxes.append((x1, y1, x2, y2))

    return boxes


def process_yolo_crops(image_path: str, yolo_results: Any, gap_threshold: int = 50) -> List[np.ndarray]:
    """
    Smart Merge document cropping:
    - 1 box: single crop
    - 2 boxes: merge when vertical gap is small, otherwise keep separate
    - >2 boxes: keep all separate
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    h, w = image.shape[:2]
    boxes = _extract_boxes_xyxy(yolo_results)
    if not boxes:
        return []

    boxes.sort(key=lambda b: b[1])  # top-to-bottom

    def _crop(box: Tuple[int, int, int, int]) -> np.ndarray:
        x1, y1, x2, y2 = _clip_xyxy_box(box, w, h)
        return image[y1:y2, x1:x2].copy()

    if len(boxes) == 1:
        return [_crop(boxes[0])]

    if len(boxes) == 2:
        b1, b2 = boxes
        gap = b2[1] - b1[3]
        if gap < gap_threshold:
            merged = (
                min(b1[0], b2[0]),
                min(b1[1], b2[1]),
                max(b1[2], b2[2]),
                max(b1[3], b2[3]),
            )
            return [_crop(merged)]
        return [_crop(b1), _crop(b2)]

    return [_crop(b) for b in boxes]


# ==========================================
# STEP 3: OPENCV OPTIMIZER
# ==========================================
def deskew(image: np.ndarray) -> np.ndarray:
    """
    Corrects small skew angles (max ±15°) to straighten text lines.
    Works in harmony with detect_and_correct_rotation for perfect alignment.
    
    Algorithm:
    1. Find non-white pixels (text/content)
    2. Use cv2.minAreaRect to get the bounding box angle
    3. Apply affine transformation to straighten
    4. Only applies if angle is within ±15° threshold (avoids over-rotation)
    
    Note: This function assumes text is already at ~0° or ~90° orientation.
          Large rotations (90°+) should be handled by detect_and_correct_rotation first.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    h, w = gray.shape[:2]

    def _rotate_any(img_src: np.ndarray, deg: float) -> np.ndarray:
        m = cv2.getRotationMatrix2D((w // 2, h // 2), deg, 1.0)
        return cv2.warpAffine(
            img_src,
            m,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

    # Text/digits mask
    thr = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    text_mask = cv2.bitwise_not(thr)

    # 1) Try Hough lines to capture wider angles (e.g. 30°, 40°, 50°)
    edges = cv2.Canny(text_mask, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180.0, threshold=60, minLineLength=max(30, w // 12), maxLineGap=10)

    angle_samples: List[float] = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = float(x2 - x1)
            dy = float(y2 - y1)
            length = (dx * dx + dy * dy) ** 0.5
            if length < 25.0:
                continue
            a = float(np.degrees(np.arctan2(dy, dx)))
            while a <= -90.0:
                a += 180.0
            while a > 90.0:
                a -= 180.0
            if -80.0 <= a <= 80.0:
                angle_samples.append(a)

    # 2) Fallback/augment with connected-components orientation
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(text_mask, connectivity=8)
    min_area = max(20, int(0.00002 * h * w))
    max_area = int(0.03 * h * w)
    for i in range(1, n_labels):
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        cw = stats[i, cv2.CC_STAT_WIDTH]
        ch = stats[i, cv2.CC_STAT_HEIGHT]
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area or area > max_area:
            continue
        aspect = max(cw, ch) / max(1.0, min(cw, ch))
        if aspect > 12.0:
            continue
        ys, xs = np.where(labels[y:y + ch, x:x + cw] == i)
        if xs.size == 0:
            continue
        pts = np.column_stack((xs + x, ys + y)).astype(np.float32)
        rect = cv2.minAreaRect(pts)
        a = float(rect[-1])
        if a < -45.0:
            a += 90.0
        if -45.0 <= a <= 45.0:
            angle_samples.append(a)

    if len(angle_samples) < 6:
        logger.debug("Deskew(text): insufficient angle evidence, skipping")
        return image

    estimated_angle = float(np.median(np.array(angle_samples, dtype=np.float32)))
    if abs(estimated_angle) < 0.2:
        logger.info("Deskew(text): no meaningful skew detected")
        return image
    if abs(estimated_angle) > 75.0:
        logger.debug(f"Deskew(text): estimated {estimated_angle:.2f}° unrealistic, skipping")
        return image

    # Try both correction directions and keep the more readable one.
    cand_a = _rotate_any(image, -estimated_angle)
    cand_b = _rotate_any(image, estimated_angle)
    score_a = _quick_ocr_readability_score(cand_a)
    score_b = _quick_ocr_readability_score(cand_b)
    if score_a >= score_b:
        applied = -estimated_angle
        corrected = cand_a
    else:
        applied = estimated_angle
        corrected = cand_b

    direction = "left" if applied > 0 else "right"
    logger.info(
        f"Deskew(text): detected ~{estimated_angle:.2f}°, rotate {abs(applied):.2f}° {direction} "
        f"(scoreA={score_a}, scoreB={score_b})"
    )
    return corrected


def _rotate_by_angle(img: np.ndarray, angle: int) -> np.ndarray:
    """Rotate image by OSD angle convention (0/90/180/270)."""
    normalized = angle % 360
    if normalized == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if normalized == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if normalized == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img


def _quick_ocr_readability_score(img_candidate: np.ndarray) -> int:
    """Fast OCR readability proxy: count alphanumeric chars recognized."""
    try:
        import pytesseract
        gray_c = cv2.cvtColor(img_candidate, cv2.COLOR_BGR2GRAY) if len(img_candidate.shape) == 3 else img_candidate
        # Keep this cheap: OCR on smaller image is enough for orientation comparison.
        s = 450 / max(gray_c.shape) if max(gray_c.shape) > 450 else 1.0
        if s != 1.0:
            gray_c = cv2.resize(gray_c, (0, 0), fx=s, fy=s)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray_c)
        thr_otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        text_a = pytesseract.image_to_string(thr_otsu, lang='fra+eng', config='--psm 6')
        score_a = sum(c.isalnum() for c in text_a)
        if score_a >= 8:
            return score_a
        # Fallback OCR pass only when first pass is weak.
        text_b = pytesseract.image_to_string(thr_otsu, lang='fra+eng', config='--psm 11')
        return max(score_a, sum(c.isalnum() for c in text_b))
    except Exception:
        return 0


def _ocr_word_confidence_score(img_candidate: np.ndarray) -> float:
    """OCR confidence proxy: combines mean token confidence and token count."""
    try:
        import pytesseract
        from pytesseract import Output
        gray_c = cv2.cvtColor(img_candidate, cv2.COLOR_BGR2GRAY) if len(img_candidate.shape) == 3 else img_candidate
        s = 700 / max(gray_c.shape) if max(gray_c.shape) > 700 else 1.0
        if s != 1.0:
            gray_c = cv2.resize(gray_c, (0, 0), fx=s, fy=s)
        thr = cv2.threshold(gray_c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        data = pytesseract.image_to_data(thr, lang='fra+eng', config='--psm 6', output_type=Output.DICT)

        conf_values: List[float] = []
        valid_tokens = 0
        for txt, conf in zip(data.get("text", []), data.get("conf", [])):
            token = (txt or "").strip()
            if len(token) < 2 or not any(ch.isalnum() for ch in token):
                continue
            try:
                conf_f = float(conf)
            except (TypeError, ValueError):
                continue
            if conf_f < 0:
                continue
            conf_values.append(conf_f)
            valid_tokens += 1

        if not conf_values:
            return 0.0

        mean_conf = float(np.mean(np.array(conf_values, dtype=np.float32)))
        token_bonus = min(30.0, valid_tokens * 1.5)
        return mean_conf + token_bonus
    except Exception:
        return 0.0


def _osd_upright_confidence(img_candidate: np.ndarray) -> float:
    """
    Returns OSD orientation confidence only when image is predicted upright (Rotate: 0),
    otherwise returns 0.0. Used as tie-breaker for CW/CCW decisions.
    """
    try:
        import pytesseract
        import re
        gray_c = cv2.cvtColor(img_candidate, cv2.COLOR_BGR2GRAY) if len(img_candidate.shape) == 3 else img_candidate
        s = 800 / max(gray_c.shape) if max(gray_c.shape) > 800 else 1.0
        if s != 1.0:
            gray_c = cv2.resize(gray_c, (0, 0), fx=s, fy=s)
        osd_output = pytesseract.image_to_osd(gray_c, config='--psm 0')
        rotate_match = re.search(r'Rotate: (\d+)', osd_output)
        conf_match = re.search(r'Orientation confidence: ([\d\.]+)', osd_output)
        if not rotate_match or not conf_match:
            return 0.0
        rotate_angle = int(rotate_match.group(1))
        confidence = float(conf_match.group(1))
        return confidence if rotate_angle == 0 else 0.0
    except Exception:
        return 0.0


def _rotation_validation_score(img_candidate: np.ndarray) -> float:
    """
    Composite orientation score:
    - OCR readability (primary)
    - OSD upright confidence (small bonus)
    """
    text_score = _quick_ocr_readability_score(img_candidate)
    upright_conf = _osd_upright_confidence(img_candidate)
    return float(text_score) + (0.3 * upright_conf)


def _rotation_metrics(img_candidate: np.ndarray) -> tuple[float, int, float]:
    """Return (composite_score, ocr_score, osd_upright_confidence)."""
    ocr_score = _quick_ocr_readability_score(img_candidate)
    conf_score = _ocr_word_confidence_score(img_candidate)
    osd_conf = _osd_upright_confidence(img_candidate)
    return float(ocr_score) + (0.7 * conf_score) + (0.3 * osd_conf), ocr_score, osd_conf


def _enforce_upright_landscape(img_candidate: np.ndarray, min_gain: float = 2.0) -> np.ndarray:
    """
    Final safeguard for card orientation:
    compare current landscape image vs 180° flipped version and keep the one
    that looks more upright/readable.
    """
    current_score, _, current_upright_conf = _rotation_metrics(img_candidate)
    flipped = cv2.rotate(img_candidate, cv2.ROTATE_180)
    flipped_score, _, flipped_upright_conf = _rotation_metrics(flipped)

    # Adaptive decision threshold:
    # - When OSD is weak on both sides, use a softer threshold.
    # - When OSD is confident, use stricter threshold to avoid flip noise.
    max_osd_conf = max(current_upright_conf, flipped_upright_conf)
    adaptive_gain = min_gain if max_osd_conf >= 6.0 else max(0.6, min_gain * 0.5)

    if flipped_score > current_score + adaptive_gain:
        logger.info(
            f"Landscape upright check: applied 180° adaptive decision "
            f"(current={current_score:.2f}/{current_upright_conf:.2f}, "
            f"flipped={flipped_score:.2f}/{flipped_upright_conf:.2f}, "
            f"adaptive_gain={adaptive_gain:.2f})"
        )
        return flipped

    logger.info(
        f"Landscape upright check: kept current orientation "
        f"(current={current_score:.2f}/{current_upright_conf:.2f}, "
        f"flipped={flipped_score:.2f}/{flipped_upright_conf:.2f}, "
        f"adaptive_gain={adaptive_gain:.2f})"
    )
    return img_candidate


def detect_and_correct_rotation(img: np.ndarray) -> np.ndarray:
    """
    Detects and corrects document rotation (90°, 180°, 270°) using Tesseract OSD.
    
    This is much more reliable than edge-detection heuristics, especially for A4 
    documents like "Certificat de Conformité" which have complex layouts and tables.
    
    Returns: Image with corrected rotation, text perfectly horizontal, upright
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    
    try:
        import pytesseract
        import re
        
        # Scale down for speed (OSD doesn't need 4K resolution)
        scale = 1.0
        max_dim = 1000
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            small = cv2.resize(gray, (0,0), fx=scale, fy=scale)
        else:
            small = gray
            
        # Run OSD (Orientation and Script Detection)
        # --psm 0 runs OSD only
        osd_output = pytesseract.image_to_osd(small, config='--psm 0')
        rotate_match = re.search(r'Rotate: (\d+)', osd_output)
        conf_match = re.search(r'Orientation confidence: ([\d\.]+)', osd_output)
        
        if rotate_match and conf_match:
            rotate_angle = int(rotate_match.group(1))
            confidence = float(conf_match.group(1))
            
            # Require high confidence (>8.0) before rotating at all.
            # Arabic+French bilingual docs (CIN, Carte Grise) confuse OSD heavily.
            if confidence < 8.0:
                logger.info(f"Auto-orientation (OSD): Low confidence ({confidence:.2f}), skipping rotation")
                return img
            
            # Extra-strict for 180° flip: require very high confidence (>12.0).
            # OSD often mistakes Arabic RTL text for an upside-down Latin document.
            if rotate_angle == 180 and confidence < 12.0:
                logger.info(f"Auto-orientation (OSD): 180° flip blocked (conf={confidence:.2f} < 12.0 threshold)")
                return img
                
            if rotate_angle in (90, 180, 270):
                candidate = _rotate_by_angle(img, rotate_angle)
                base_score = _rotation_validation_score(img)
                cand_score = _rotation_validation_score(candidate)
                min_gain = 8.0 if rotate_angle == 180 else 5.0
                score_gain = cand_score - base_score

                if score_gain < min_gain:
                    logger.info(
                        f"Auto-orientation (OSD): rotation {rotate_angle}° rejected "
                        f"(conf={confidence:.2f}, gain={score_gain:.2f} < {min_gain:.2f})"
                    )
                    return img

                if rotate_angle == 90:
                    logger.info(
                        f"Auto-orientation (OSD): 90° CW applied "
                        f"(conf={confidence:.2f}, gain={score_gain:.2f})"
                    )
                elif rotate_angle == 180:
                    logger.info(
                        f"Auto-orientation (OSD): 180° applied "
                        f"(conf={confidence:.2f}, gain={score_gain:.2f})"
                    )
                else:
                    logger.info(
                        f"Auto-orientation (OSD): 90° CCW applied "
                        f"(conf={confidence:.2f}, gain={score_gain:.2f})"
                    )
                return candidate
            else:
                logger.info(f"Auto-orientation (OSD): Upright (0°), no rotation needed (conf: {confidence:.2f})")
                return img
                
    except Exception as e:
        logger.warning(f"OSD rotation check failed: {e}")
        
    return img


def apply_clahe_lab(img: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to the L channel
    of LAB color space to enhance contrast while preserving color information.
    This helps reduce flash glare while keeping colors for LLM vision models.
    """
    # Convert BGR to LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    
    # Split LAB channels
    l_channel, a_channel, b_channel = cv2.split(lab)
    
    # Apply CLAHE to L (Luminance) channel
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l_channel_clahe = clahe.apply(l_channel)
    
    # Merge back the channels
    lab_enhanced = cv2.merge([l_channel_clahe, a_channel, b_channel])
    
    # Convert back to BGR
    img_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    
    return img_enhanced


def unsharp_mask(img: np.ndarray, kernel_size: int = 5, sigma: float = 1.0, strength: float = 1.2) -> np.ndarray:
    """
    Apply unsharp mask to sharpen text and details.
    This makes thin text (like expiration dates) crisp and clear.
    
    Args:
        img: Input image (BGR)
        kernel_size: Size of the Gaussian blur kernel (odd number)
        sigma: Standard deviation for Gaussian blur
        strength: Strength of sharpening (1.0 = original, >1.0 = more sharpening)
    """
    # Ensure kernel size is odd
    if kernel_size % 2 == 0:
        kernel_size += 1
    
    # Create blurred version
    blurred = cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)
    
    # Compute sharpened image: original + strength * (original - blurred)
    sharpened = cv2.addWeighted(img, 1.0 + strength, blurred, -strength, 0)
    
    # Clip values to valid range [0, 255]
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
    
    return sharpened


def yolo_crop_document(img: np.ndarray, conf_threshold: float = 0.3, margin_pct: float = 0.15) -> List[np.ndarray]:
    """
    Use custom YOLO models to detect and crop documents (CIN, Permis, Carte Grise) from a photo.
    Returns: List of cropped images. Empty list if none detected.
    """
    models = get_yolo_models()
    if not models:
        logger.warning("YOLO: models not available, skipping")
        return []
    
    h, w = img.shape[:2]
    all_valid_boxes = []
    obb_document_found = False
    
    # Separate OBB vs classic models
    obb_models = [(m, name, mtype) for m, name, mtype in models if mtype == "obb"]
    classic_models = [(m, name, mtype) for m, name, mtype in models if mtype == "classic"]
    
    # OBB classes that represent a full document (not just a title label)
    OBB_DOCUMENT_CLASSES = {"titre_francais"}
    OBB_TITRE_LABEL_CLASSES = {"titre_arabe", "titre_propriete"}
    OBB_MIN_AREA_PCT = 40.0
    
    # Variables to track OBB detections to enforce semantic verification
    obb_pending_full_docs = []    # Store potential large document structures
    obb_has_titre_label = False  # Did we find a specific titre label (arabe/propriete)?
    obb_is_titre = False         # Titre hint flag to suppress classic item splits
    
    # === PHASE 1: OBB models (document-type identifier) ===
    for model, model_source, model_type in obb_models:
        try:
            results = model(img, verbose=False)
            if not results or len(results) == 0:
                continue
            result = results[0]
            is_obb = hasattr(result, 'obb') and result.obb is not None and len(result.obb) > 0
            if not is_obb:
                logger.info(f"YOLO-OBB [{model_source}]: 0 raw detections")
                continue
            
            obb = result.obb
            logger.info(f"YOLO-OBB [{model_source}]: {len(obb)} raw detection(s)")
            
            for det_idx in range(len(obb)):
                conf = float(obb.conf[det_idx])
                cls_id = int(obb.cls[det_idx])
                cls_name = model.names[cls_id] if cls_id < len(model.names) else f"class_{cls_id}"
                corners = obb.xyxyxyxy[det_idx].cpu().numpy().astype(np.float32)
                xywhr = obb.xywhr[det_idx].cpu().numpy()
                angle_deg = float(np.degrees(xywhr[4]))
                rect = cv2.minAreaRect(corners)
                box_w, box_h = rect[1]
                box_area = box_w * box_h
                area_pct = box_area / (h * w) * 100
                
                logger.info(
                    f"  → [{cls_name}] conf={conf:.3f} | area={area_pct:.1f}% | "
                    f"angle={angle_deg:.1f}° | corners={corners.astype(int).tolist()}"
                )
                
                if conf < conf_threshold:
                    logger.info(f"    ✗ FILTERED: conf {conf:.3f} < threshold {conf_threshold}")
                    continue
                
                if cls_name in OBB_DOCUMENT_CLASSES and area_pct >= OBB_MIN_AREA_PCT:
                    # Check aspect ratio to reject wide ID cards misclassified as A4 titles
                    # Using min(w,h) and max(w,h) ensures orientation independence
                    min_dim = min(box_w, box_h)
                    max_dim = max(box_w, box_h)
                    
                    # Assume Titre is roughly A4 (1.41) or folded square (~1.0)
                    # ID cards are wide (1.58 ratio). So if max/min is > 1.35 and it's horizontal-looking,
                    # we might want to be careful. But simpler: just ratio > 1.35 means it's a card.
                    ratio = max_dim / min_dim if min_dim > 0 else 0
                    
                    if ratio > 1.35 and "titre" in cls_name:
                        logger.info(f"    ✗ FILTERED: ratio {ratio:.2f} > 1.35 (looks like an ID card, not a tall Titre)")
                        continue
                        
                    if conf < 0.60:
                        logger.info(f"    ✗ FILTERED (OBB full doc): conf {conf:.3f} < 0.60 (too uncertain, preventing false-positive bypass)")
                        continue
                        
                    logger.info(f"    [Pending] OBB full doc queued: ratio={ratio:.2f}, conf={conf:.2f}")
                    obb_pending_full_docs.append({
                        'corners': corners, 'conf': conf, 'cls_name': cls_name, 
                        'model_source': model_source, 'ratio': ratio
                    })
                else:
                    if cls_name in OBB_TITRE_LABEL_CLASSES and conf > 0.20:
                        obb_is_titre = True
                        obb_has_titre_label = True
                    logger.info(f"    ℹ OBB label '{cls_name}' (area={area_pct:.1f}%) — not a crop target")
                    
            # Auto-validate the full documents ONLY IF a specific semantic titre label was also found
            for doc in obb_pending_full_docs:
                if obb_has_titre_label:
                    logger.info(f"    ✓ ACCEPTED (OBB full document Validated! Found required inner titre label)")
                    x1 = float(doc['corners'][:, 0].min())
                    y1 = float(doc['corners'][:, 1].min())
                    x2 = float(doc['corners'][:, 0].max())
                    y2 = float(doc['corners'][:, 1].max())
                    all_valid_boxes.append((x1, y1, x2, y2, doc['conf'], doc['cls_name'], doc['model_source'], doc['corners']))
                    obb_document_found = True
                else:
                    logger.info(f"    ✗ FILTERED (OBB full doc rejected): Found frame '{doc['cls_name']}' but no inner Semantic Labels (titre_arabe/propriete) found on page.")

        except Exception as e:
            logger.warning(f"YOLO-OBB inference failed for {model_source}: {e}")
            continue
    
    # === PHASE 2: Classic models — ONLY if OBB didn't find the document ===
    if obb_document_found:
        logger.info("YOLO: OBB detected full document → skipping classic models (avoids folded-doc split)")
    else:
        for model, model_source, model_type in classic_models:
            try:
                results = model(img, verbose=False)
                if not results or len(results) == 0:
                    continue
                result = results[0]
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    logger.info(f"YOLO [{model_source}]: 0 raw detections")
                    continue
                
                logger.info(f"YOLO [{model_source}]: {len(boxes)} raw detection(s)")
                
                for box in boxes:
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    box_area = (x2 - x1) * (y2 - y1)
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id] if cls_id < len(model.names) else f"class_{cls_id}"
                    area_pct = box_area / (h * w) * 100
                    
                    logger.info(
                        f"  → [{cls_name}] conf={conf:.3f} | area={area_pct:.1f}% | "
                        f"box=({int(x1)},{int(y1)})-({int(x2)},{int(y2)})"
                    )
                    
                    if conf < conf_threshold:
                        logger.info(f"    ✗ FILTERED: conf {conf:.3f} < threshold {conf_threshold}")
                        continue
                    if obb_is_titre and cls_name == "item":
                        logger.info(f"    ✗ FILTERED: skipped 'item' split because OBB detected a Titre hint")
                        continue
                    if "person" in model.names.values() and cls_name not in ["book"]:
                        logger.info(f"    ✗ FILTERED: COCO class '{cls_name}' skipped")
                        continue
                    if box_area / (h * w) < 0.03:
                        logger.info(f"    ✗ FILTERED: area {area_pct:.1f}% < 3% (noise)")
                        continue
                    if cls_name == 'paper' and box_area / (h * w) < 0.40:
                        logger.info(f"    ✗ FILTERED: 'paper' ghost ({area_pct:.1f}% < 40%)")
                        continue
                    
                    logger.info(f"    ✓ ACCEPTED")
                    all_valid_boxes.append((x1, y1, x2, y2, conf, cls_name, model_source, None))
            except Exception as e:
                logger.warning(f"YOLO inference failed for {model_source}: {e}")
                continue

    if not all_valid_boxes:
        logger.info("YOLO: no valid detections found from any model")
        return []

    # Sort by confidence first; class-specific conflicts are handled by duplicate resolver below.
    all_valid_boxes.sort(key=lambda b: b[4], reverse=True)

    def overlap_metrics(b1, b2):
        x1_1, y1_1, x2_1, y2_1 = b1[:4]
        x1_2, y1_2, x2_2, y2_2 = b2[:4]
        ix1 = max(x1_1, x1_2)
        iy1 = max(y1_1, y1_2)
        ix2 = min(x2_1, x2_2)
        iy2 = min(y2_1, y2_2)

        iw = max(0, ix2 - ix1)
        ih = max(0, iy2 - iy1)
        inter_area = iw * ih
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        if area1 <= 0 or area2 <= 0:
            return 0.0, 0.0, 0.0

        min_area_overlap = inter_area / min(area1, area2)
        union = area1 + area2 - inter_area
        iou = inter_area / union if union > 0 else 0.0
        containment = inter_area / max(area1, area2)
        return min_area_overlap, iou, containment

    final_boxes = []
    for box in all_valid_boxes:
        replaced_existing = False
        rejected_as_duplicate = False

        for i, kept in enumerate(final_boxes):
            min_overlap, iou, containment = overlap_metrics(box, kept)
            if min_overlap < 0.70:
                continue

            cand_conf, kept_conf = box[4], kept[4]
            cand_cls, kept_cls = box[5], kept[5]
            cand_src, kept_src = box[6], kept[6]

            # Same-region duplicate resolution:
            # - Prefer item over paper when overlapping heavily.
            # - Otherwise keep the higher confidence candidate.
            if cand_cls == "item" and kept_cls == "paper":
                final_boxes[i] = box
                replaced_existing = True
                logger.info(
                    f"YOLO dedup: replaced kept paper with item "
                    f"(overlap={min_overlap:.2f}, iou={iou:.2f}, contain={containment:.2f}) "
                    f"[new={cand_src}, old={kept_src}]"
                )
                break

            if cand_cls == "paper" and kept_cls == "item":
                rejected_as_duplicate = True
                logger.info(
                    f"YOLO dedup: suppressed paper duplicate vs item "
                    f"(overlap={min_overlap:.2f}, iou={iou:.2f}, contain={containment:.2f}) "
                    f"[paper={cand_src}, item={kept_src}]"
                )
                break

            if cand_conf > kept_conf:
                final_boxes[i] = box
                replaced_existing = True
                logger.info(
                    f"YOLO dedup: replaced lower-confidence duplicate "
                    f"{kept_cls}({kept_conf:.2f}) with {cand_cls}({cand_conf:.2f}) "
                    f"(overlap={min_overlap:.2f}, iou={iou:.2f}, contain={containment:.2f})"
                )
                break

            rejected_as_duplicate = True
            logger.info(
                f"YOLO dedup: suppressed duplicate {cand_cls}({cand_conf:.2f}) "
                f"behind kept {kept_cls}({kept_conf:.2f}) "
                f"(overlap={min_overlap:.2f}, iou={iou:.2f}, contain={containment:.2f})"
            )
            break

        if not replaced_existing and not rejected_as_duplicate:
            final_boxes.append(box)
            logger.info(
                f"YOLO dedup: kept distinct box {box[5]}({box[4]:.2f}) from {box[6]}"
            )

    def _box_center(box):
        x1, y1, x2, y2 = box[:4]
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def _axis_overlap_ratio(a1, a2, b1, b2):
        inter = max(0.0, min(a2, b2) - max(a1, b1))
        len_a = max(1e-6, a2 - a1)
        len_b = max(1e-6, b2 - b1)
        return inter / min(len_a, len_b)

    def _is_strict_near_duplicate(b1, b2):
        x1_1, y1_1, x2_1, y2_1 = b1[:4]
        x1_2, y1_2, x2_2, y2_2 = b2[:4]
        area1 = max(1.0, (x2_1 - x1_1) * (y2_1 - y1_1))
        area2 = max(1.0, (x2_2 - x1_2) * (y2_2 - y1_2))
        min_overlap, iou, containment = overlap_metrics(b1, b2)

        cx1, cy1 = _box_center(b1)
        cx2, cy2 = _box_center(b2)
        center_dist = ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5
        diag = max(1.0, (w ** 2 + h ** 2) ** 0.5)
        center_ratio = center_dist / diag

        size_ratio = area1 / area2 if area1 >= area2 else area2 / area1
        x_overlap = _axis_overlap_ratio(x1_1, x2_1, x1_2, x2_2)
        y_overlap = _axis_overlap_ratio(y1_1, y2_1, y1_2, y2_2)

        is_near_dup = (
            min_overlap >= 0.78
            and center_ratio <= 0.12
            and size_ratio <= 1.40
            and (iou >= 0.50 or containment >= 0.65)
            and x_overlap >= 0.85
            and y_overlap >= 0.78
        )
        return is_near_dup, {
            "overlap": min_overlap,
            "iou": iou,
            "contain": containment,
            "center": center_ratio,
            "size_ratio": size_ratio,
            "x_overlap": x_overlap,
            "y_overlap": y_overlap
        }

    def _prefer_box(a, b):
        # Prefer item over paper only when both are near-duplicates.
        if a[5] == "item" and b[5] == "paper":
            return a
        if a[5] == "paper" and b[5] == "item":
            return b
        return a if a[4] >= b[4] else b

    # Strict second pass: merge only near-identical boxes.
    strict_boxes = []
    for box in final_boxes:
        merged = False
        for i, kept in enumerate(strict_boxes):
            is_dup, m = _is_strict_near_duplicate(box, kept)
            if not is_dup:
                continue
            winner = _prefer_box(box, kept)
            strict_boxes[i] = winner
            loser = kept if winner is box else box
            logger.info(
                "YOLO strict dedup: merged near-duplicate "
                f"{loser[5]}({loser[4]:.2f},{loser[6]}) into "
                f"{winner[5]}({winner[4]:.2f},{winner[6]}) "
                f"[ov={m['overlap']:.2f},iou={m['iou']:.2f},cont={m['contain']:.2f},"
                f"center={m['center']:.3f},size={m['size_ratio']:.2f},"
                f"xov={m['x_overlap']:.2f},yov={m['y_overlap']:.2f}]"
            )
            merged = True
            break
        if not merged:
            strict_boxes.append(box)

    final_boxes = strict_boxes

    # Sort boxes top-to-bottom based on y1 coordinate for consistent ordering
    final_boxes.sort(key=lambda b: b[1])

    # Smart Merge for exactly two detections:
    # merge only when boxes are vertically stacked, strongly aligned on X axis,
    # and the gap is small relative to card height (folded single document).
    if len(final_boxes) == 2:
        b1, b2 = final_boxes
        vertical_gap = float(b2[1] - b1[3])
        h1, h2 = float(b1[3] - b1[1]), float(b2[3] - b2[1])
        w1, w2 = float(b1[2] - b1[0]), float(b2[2] - b2[0])
        min_h = max(1.0, min(h1, h2))
        width_ratio = max(w1, w2) / max(1.0, min(w1, w2))
        x_overlap = _axis_overlap_ratio(float(b1[0]), float(b1[2]), float(b2[0]), float(b2[2]))
        cx1 = (float(b1[0]) + float(b1[2])) / 2.0
        cx2 = (float(b2[0]) + float(b2[2])) / 2.0
        center_x_delta = abs(cx1 - cx2) / max(1.0, float(w))

        adaptive_gap_threshold = max(float(SMART_MERGE_GAP_THRESHOLD), 0.25 * min_h)
        should_merge = (
            vertical_gap >= 0.0
            and vertical_gap < adaptive_gap_threshold
            and x_overlap >= 0.70
            and width_ratio <= 1.40
            and center_x_delta <= 0.12
        )

        if should_merge:
            merged_box = (
                min(b1[0], b2[0]),
                min(b1[1], b2[1]),
                max(b1[2], b2[2]),
                max(b1[3], b2[3]),
                max(b1[4], b2[4]),
                "merged",
                "smart-merge",
                None,
            )
            logger.info(
                f"YOLO smart-merge: merged 2 boxes into 1 "
                f"(gap={vertical_gap:.1f}px < {adaptive_gap_threshold:.1f}px, "
                f"xov={x_overlap:.2f}, wr={width_ratio:.2f}, cx={center_x_delta:.3f})"
            )
            final_boxes = [merged_box]
        else:
            logger.info(
                f"YOLO smart-merge: kept 2 separate boxes "
                f"(gap={vertical_gap:.1f}px, th={adaptive_gap_threshold:.1f}px, "
                f"xov={x_overlap:.2f}, wr={width_ratio:.2f}, cx={center_x_delta:.3f})"
            )
    
    crops = []
    for x1, y1, x2, y2, conf, cls_name, model_source, obb_corners in final_boxes:
        
        # OBB crop: perspective-warp the rotated bounding box into a clean rectangle
        if obb_corners is not None:
            # Expand OBB corners outward by margin_pct to capture full document
            # For 'titre' documents, best2.pt often misses the bottom dates, so we aggressively expand the box
            effective_margin = 0.25 if "titre" in cls_name else margin_pct
            
            center = obb_corners.mean(axis=0)
            expanded_corners = center + (obb_corners - center) * (1.0 + effective_margin)
            # Clip to image bounds
            expanded_corners[:, 0] = np.clip(expanded_corners[:, 0], 0, w - 1)
            expanded_corners[:, 1] = np.clip(expanded_corners[:, 1], 0, h - 1)
            
            rect = cv2.minAreaRect(expanded_corners)
            dst_w, dst_h = int(rect[1][0]), int(rect[1][1])
            if dst_w < 10 or dst_h < 10:
                continue
            # Order corners: top-left, top-right, bottom-right, bottom-left
            ordered = cv2.boxPoints(rect)
            ordered = ordered[np.argsort(ordered[:, 1])]  # sort by y
            top = ordered[:2][np.argsort(ordered[:2, 0])]  # top row sorted by x
            bot = ordered[2:][np.argsort(ordered[2:, 0])]  # bottom row sorted by x
            src_pts = np.array([top[0], top[1], bot[1], bot[0]], dtype=np.float32)
            dst_pts = np.array([[0, 0], [dst_w, 0], [dst_w, dst_h], [0, dst_h]], dtype=np.float32)
            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
            cropped = cv2.warpPerspective(img, M, (dst_w, dst_h))
            logger.info(
                f"YOLO-OBB crop: {cls_name} (conf={conf:.2f}) → perspective-warp {dst_w}x{dst_h} (margin={margin_pct:.0%})"
            )
        else:
            # Standard axis-aligned crop with margin
            box_w = x2 - x1
            box_h = y2 - y1
            margin_x = int(box_w * margin_pct)
            margin_y = int(box_h * margin_pct)
            crop_x1 = max(0, int(x1) - margin_x)
            crop_y1 = max(0, int(y1) - margin_y)
            crop_x2 = min(w, int(x2) + margin_x)
            crop_y2 = min(h, int(y2) + margin_y)
            cropped = img[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if cropped.size > 0:
            ch_crop, cw_crop = cropped.shape[:2]
            # Reject crops that are too small to be a real document
            # A real card (CIN/Permis/Carte Grise) is at least 250px on each side
            if cw_crop < 250 or ch_crop < 250:
                logger.warning(f"YOLO: crop too small ({cw_crop}x{ch_crop}), rejecting")
                continue
            crop_gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
            crop_std = crop_gray.std()
            if crop_std >= 10.0:
                logger.info(
                    f"YOLO crop kept: {cls_name} (conf={conf:.2f}, source={model_source}) "
                    f"→ {cw_crop}x{ch_crop}"
                )
                crops.append(cropped)
            else:
                logger.warning(f"YOLO: crop looks blank (std={crop_std:.1f}), rejecting")
                
    return crops


def _opencv_crop_card(img: np.ndarray) -> List[np.ndarray]:
    """
    OpenCV fallback — traditional contour-based document crop.
    Handles: CIN, Carte Grise, Permis (card-sized ~1.58:1) and
             Certificat de Conformité (A4 ~1.41:1).
    
    Multi-strategy approach:
    1. Edge detection with multiple Canny thresholds
    2. Color-based segmentation (CIN green, white documents)
    3. Contour scoring: aspect ratio match > rectangularity > area
    """
    h, w = img.shape[:2]
    original_area = h * w
    min_doc_area = original_area * 0.05  # At least 5% of image

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    candidates = []
    
    # --- Strategy A: Multiple Canny thresholds ---
    for canny_lo, canny_hi, dilate_iter in [(15, 60, 2), (30, 100, 2), (50, 150, 1)]:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, canny_lo, canny_hi)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=dilate_iter)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        candidates.extend(contours)
    
    # --- Strategy B: Color-based segmentation ---
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Green detection (CIN)
    green_mask = cv2.inRange(hsv, (25, 20, 60), (90, 255, 220))
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE,
                                   cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)), iterations=3)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN,
                                   cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=1)
    cnts_green, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates.extend(cnts_green)
    
    # White/light document detection
    white_mask = cv2.inRange(hsv, (0, 0, 140), (180, 60, 255))
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE,
                                   cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)), iterations=3)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN,
                                   cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)), iterations=1)
    cnts_white, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates.extend(cnts_white)

    if not candidates:
        logger.info("OpenCV crop: no contours found, returning original")
        return [img]

    # --- Score contours as potential documents ---
    CARD_RATIO = 1.585    # CIN, Carte Grise, Permis (85.6mm × 54mm)
    A4_RATIO = 1.414      # A4 paper (297mm × 210mm)
    KNOWN_RATIOS = [CARD_RATIO, A4_RATIO]
    
    scored = []
    seen_rects = set()
    
    for cnt in candidates:
        area = cv2.contourArea(cnt)
        if area < min_doc_area:
            continue
        
        area_ratio = area / original_area
        if area_ratio > 0.85:
            continue
        
        peri = cv2.arcLength(cnt, True)
        best_approx = None
        for eps in [0.015, 0.02, 0.03, 0.04, 0.05]:
            approx = cv2.approxPolyDP(cnt, eps * peri, True)
            if len(approx) == 4:
                best_approx = approx
                break
            elif 4 < len(approx) <= 6 and best_approx is None:
                best_approx = approx
        
        if best_approx is None:
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)
            if len(approx) < 4 or len(approx) > 10:
                continue
            best_approx = approx
        
        rot_rect = cv2.minAreaRect(cnt)
        (cx, cy), (rw, rh), angle = rot_rect
        if rw < 50 or rh < 50:
            continue
        
        rect_key = (int(cx/50), int(cy/50), int(max(rw,rh)/50))
        if rect_key in seen_rects:
            continue
        seen_rects.add(rect_key)
        
        aspect = max(rw, rh) / min(rw, rh)
        
        ratio_dist = min(abs(aspect - r) for r in KNOWN_RATIOS)
        ratio_score = max(0, 1.0 - ratio_dist / 0.5)
        
        rect_area = rw * rh
        rect_fill = area / (rect_area + 1e-5)
        
        if area_ratio < 0.15:
            area_score = area_ratio / 0.15
        elif area_ratio <= 0.60:
            area_score = 1.0
        else:
            area_score = max(0, 1.0 - (area_ratio - 0.60) / 0.25)
        
        sides_bonus = 1.0 if len(best_approx) == 4 else 0.5
        
        score = (ratio_score * 0.40 +
                 rect_fill * 0.20 +
                 area_score * 0.20 +
                 sides_bonus * 0.20)
        
        scored.append({
            'contour': cnt, 'approx': best_approx, 'area': area,
            'score': score, 'rot_rect': rot_rect,
            'bbox': cv2.boundingRect(best_approx), 'aspect': aspect,
            'fill': rect_fill, 'area_ratio': area_ratio,
            'ratio_score': ratio_score, 'n_sides': len(best_approx)
        })
    
    if not scored:
        logger.info("OpenCV crop: no valid document contour found, returning original")
        return [img]
    
    scored.sort(key=lambda s: s['score'], reverse=True)
    for i, s in enumerate(scored[:3]):
        logger.info(f"OpenCV crop candidate #{i+1}: aspect={s['aspect']:.2f}, "
                     f"sides={s['n_sides']}, fill={s['fill']:.0%}, "
                     f"area={s['area_ratio']:.0%}, ratio_match={s['ratio_score']:.2f}, "
                     f"SCORE={s['score']:.3f}")
    
    crops = []
    # To prevent overlapping crops (e.g., a card and a smaller piece inside it)
    def is_overlap(b1, b2):
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        # Check if one rectangle is inside another or intersects significantly
        intersect_x = max(0, min(x1+w1, x2+w2) - max(x1, x2))
        intersect_y = max(0, min(y1+h1, y2+h2) - max(y1, y2))
        inter_area = intersect_x * intersect_y
        area1 = w1 * h1
        area2 = w2 * h2
        # If intersection is more than 30% of the smaller area, they overlap
        if inter_area > 0.3 * min(area1, area2):
            return True
        return False
        
    used_boxes = []
    
    # Sort by y-coordinate to keep top-to-bottom order for final output
    scored_valid = []
    
    for s in scored:
        if s['score'] < 0.65: continue
        
        box = s['bbox']
        overlap = False
        for u_box in used_boxes:
            if is_overlap(box, u_box):
                overlap = True
                break
                
        if not overlap:
            used_boxes.append(box)
            scored_valid.append(s)
            
    if not scored_valid:
        return [img]
        
    # Sort top-to-bottom
    scored_valid.sort(key=lambda s: s['bbox'][1])
    
    for s in scored_valid:
        x, y, bw, bh = s['bbox']
        margin_x = int(bw * 0.15)
        margin_y = int(bh * 0.15)
        
        new_x = max(0, x - margin_x)
        new_y = max(0, y - margin_y)
        final_w = min(w - new_x, bw + 2 * margin_x)
        final_h = min(h - new_y, bh + 2 * margin_y)
        
        cropped = img[new_y:new_y+final_h, new_x:new_x+final_w]
        if cropped.size > 0 and cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY).std() >= 10.0:
            crops.append(cropped)
            
    if not crops:
        return [img]
        
    return crops


def auto_crop_card(img: np.ndarray) -> List[np.ndarray]:
    """
    Smart document crop — YOLOv8 primary, OpenCV fallback.
    """
    yolo_result = yolo_crop_document(img)
    if yolo_result and len(yolo_result) > 0:
        logger.info(f"Auto-crop: used YOLOv8 detection ✓ (Found {len(yolo_result)} docs)")
        return yolo_result
    
    logger.info("Auto-crop: YOLO didn't find document, falling back to OpenCV")
    return _opencv_crop_card(img)


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]       # top-left: smallest sum
    rect[2] = pts[np.argmax(s)]       # bottom-right: largest sum
    rect[1] = pts[np.argmin(d)]       # top-right: smallest difference
    rect[3] = pts[np.argmax(d)]       # bottom-left: largest difference
    return rect


def optimize_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Advanced preprocessing pipeline for better OCR accuracy:
    0. Auto-crop card (remove white borders / A4 background)
    1. Upscale small images (improves digit recognition)
    2. Convert to grayscale
    3. Denoise (reduce noise while preserving edges)
    4. CLAHE (improve contrast adaptively)
    5. Deskew (straighten tilted documents)
    """
    # 0. Auto-crop: isolate the card from blank backgrounds
    img = auto_crop_card(img)

    h, w = img.shape[:2]
    
    # 1. Upscale if image is too small (helps with digit recognition like 6 vs 9)
    min_dimension = 2000
    if max(h, w) < min_dimension:
        scale = min_dimension / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        logger.info(f"Upscaled image: {w}x{h} → {img.shape[1]}x{img.shape[0]}")
    
    # 2. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. Light denoise - preserve text details
    denoised = cv2.bilateralFilter(gray, 5, 75, 75)
    
    # 4. CLAHE - Contrast Limited Adaptive Histogram Equalization (lighter)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    # 5. Deskew
    bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    deskewed = deskew(bgr)
    
    logger.info("OpenCV preprocessing: crop → upscale → denoise → CLAHE → deskew")
    return deskewed

def get_image_metrics(img: np.ndarray):
    """Calculates blur score with contrast normalization + blue ink handwriting detection."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    gray = cv2.equalizeHist(gray)  # Normalize lighting before blur calc
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    # Keyword-based handwriting detection via simple OCR to catch CERTIFICAT DE CONFORMITE
    is_handwritten = False
    try:
        import pytesseract
        text = pytesseract.image_to_string(gray, lang='fra', config='--psm 6')
        if 'CONFORMITE' in text.upper() or 'CERTIFICAT' in text.upper() or 'PROPRIETE' in text.upper():
            is_handwritten = True
            logger.info("Detected CONFORMITE/CERTIFICAT/PROPRIETE — marking as A4/Portrait")
    except Exception as e:
        logger.warning(f"Handwriting keyword detection failed: {e}")

    return round(blur_score, 2), is_handwritten

def optimize_for_llm_image(img: np.ndarray, is_hw: bool = False) -> List[tuple]:
    """
    Robust preprocessing pipeline. Returns a list of tuples:
    [(cropped_img1, final_img1), (cropped_img2, final_img2), ...]
    """
    final_original = img.copy()
    crops = auto_crop_card(final_original)
    results = []
    
    for idx, piece in enumerate(crops):
        raw_piece = piece.copy()
        final = raw_piece
        
        ch, cw = raw_piece.shape[:2]
        aspect_ratio = max(ch, cw) / float(min(ch, cw)) if min(ch, cw) > 0 else 1.0
        
        # Card-like docs (CIN/Permis/Carte Grise) can be slightly distorted after crop.
        # Use a looser ratio threshold to still force portrait->landscape correction.
        is_card_like = (aspect_ratio >= 1.20) and not is_hw
        
        # Rotation disabled before LLM (kept as comments on purpose).
        # if is_card_like and ch > cw:
        #     # Card is in Portrait — rotate to Landscape.
        #     # Skip pre-OSD here: OSD can flip portrait Arabic/French cards incorrectly.
        #     candidate_cw = cv2.rotate(raw_piece, cv2.ROTATE_90_CLOCKWISE)
        #     candidate_ccw = cv2.rotate(raw_piece, cv2.ROTATE_90_COUNTERCLOCKWISE)
        #
        #     score_cw, _, conf_cw = _rotation_metrics(candidate_cw)
        #     score_ccw_base, _, conf_ccw = _rotation_metrics(candidate_ccw)
        #     score_ccw = score_ccw_base + 0.8  # slight prior for CIN
        #
        #     # CW override requires BOTH strong score lead and strong OSD upright evidence.
        #     if (score_cw > score_ccw + 12.0) and (conf_cw >= 8.0) and (conf_cw > conf_ccw + 2.0):
        #         logger.info("Portrait→Landscape: chose 90° CW (score+OSD override)")
        #         final = candidate_cw
        #     else:
        #         logger.info("Portrait→Landscape: chose 90° CCW (default)")
        #         final = candidate_ccw
        # else:
        #     # For non-portrait-card cases, keep OSD-based correction.
        #     final = detect_and_correct_rotation(raw_piece)
        final = raw_piece

        cropped = final.copy()
        
        final = apply_clahe_lab(final, clip_limit=2.0, tile_size=8)
        final = unsharp_mask(final, kernel_size=5, sigma=1.0, strength=1.2)
        # final = deskew(final)

        # if is_card_like:
        #     # Run anti-reverse after enhancement so OCR/OSD sees clearer text.
        #     final = _enforce_upright_landscape(final)
        
        h, w = final.shape[:2]
        max_dimension = 1800
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            final = cv2.resize(final, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            
        results.append((cropped, final))
        
    return results


def encode_image_to_base64(img: np.ndarray) -> str:
    """Encode a numpy image to a data:image/jpeg;base64,... string."""
    ok, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    b64 = base64.b64encode(buf).decode('utf-8')
    logger.info(f"Page optimized → {len(b64):,} base64 chars")
    return f"data:image/jpeg;base64,{b64}"


def optimize_for_llm(img: np.ndarray) -> list[str]:
    """Full pipeline: optimize image + encode to base64 data URI."""
    results = optimize_for_llm_image(img)
    return [encode_image_to_base64(opt) for _, opt in results]


# ==========================================
# PDF OUTPUT GENERATOR
# ==========================================
def generate_pdf_from_images(optimized_images: list) -> str:
    """
    Takes a list of optimized OpenCV images (numpy arrays, BGR)
    and compiles them into a single PDF using PyMuPDF.
    Returns the PDF as a base64-encoded string.
    """
    if not optimized_images:
        return ""

    pdf_doc = fitz.open()  # Create empty PDF

    for idx, img in enumerate(optimized_images):
        # Encode the numpy array as JPEG bytes
        ok, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not ok:
            logger.warning(f"PDF generation: failed to encode page {idx}, skipping")
            continue

        img_bytes = buf.tobytes()

        # Create a new page with the image dimensions
        h, w = img.shape[:2]
        # Convert pixels to points (72 DPI for PDF)
        # We'll fit the image to A4-ish proportions but keep aspect ratio
        max_width = 595.0   # A4 width in points
        max_height = 842.0  # A4 height in points
        scale = min(max_width / w, max_height / h)
        page_w = w * scale
        page_h = h * scale

        page = pdf_doc.new_page(width=page_w, height=page_h)

        # Insert the image to fill the entire page
        rect = fitz.Rect(0, 0, page_w, page_h)
        page.insert_image(rect, stream=img_bytes)

        logger.info(f"PDF page {idx + 1}: {w}x{h}px → {page_w:.0f}x{page_h:.0f}pt")

    # Write PDF to bytes
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
    logger.info(f"Generated PDF: {len(optimized_images)} pages, {len(pdf_bytes) // 1024}KB")
    return pdf_b64


# ==========================================
# STEP 1: ENTRY POINT
# POST /api/v1/analyze-bundle
# Accepts: pdf (optional) + image (optional) — at least one required
# ==========================================
@app.post("/api/v1/analyze-bundle", tags=["OCR Pipeline"])
async def analyze_bundle(
    file: UploadFile = File(..., description="PDF or Image (JPG/PNG) — auto-detected"),
):
    """
    Accepts a single file: PDF (carte grise) or Image (CIN/photo).
    Auto-detects the file type, rasterizes at 150 DPI (PDF) or decodes (Image),
    and returns optimized base64 images ready for GPT Vision in n8n.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ['pdf', 'png', 'jpg', 'jpeg']:
        raise HTTPException(status_code=400, detail=f"Unsupported file: .{ext}. Accepted: pdf, jpg, jpeg, png")

    file_bytes = await file.read()
    logger.info(f"Received: {file.filename} ({len(file_bytes)//1024}KB) — type: {ext}")

    all_pages = []
    cropped_images = []    # Cropped-only images for user PDF (clear, no filters)
    optimized_images = []  # Fully filtered images for debug PDF (what LLM sees)

    if ext == 'pdf':
        try:
            imgs = crack_pdf(file_bytes)
            for idx, img in enumerate(imgs):
                blur, is_hw = get_image_metrics(img)
                crop_results = optimize_for_llm_image(img, is_hw=is_hw)
                for c_idx, (cropped_img, opt_img) in enumerate(crop_results):
                    cropped_images.append(cropped_img)
                    optimized_images.append(opt_img)
                    b64 = encode_image_to_base64(opt_img)
                    c_b64 = encode_image_to_base64(cropped_img)
                    all_pages.append({
                        "source": "pdf",
                        "filename": file.filename,
                        "page": f"{idx}_{c_idx}",
                        "image_base64": b64,
                        "cropped_base64": c_b64,
                        "blur_score": blur,
                        "is_handwritten": is_hw,
                        "doc_type": "HANDWRITTEN" if is_hw else "STANDARD"
                    })
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF error: {e}")
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

    else:  # jpg, jpeg, png
        try:
            img = crack_image(file_bytes)
            blur, is_hw = get_image_metrics(img)
            crop_results = optimize_for_llm_image(img, is_hw=is_hw)
            for c_idx, (cropped_img, opt_img) in enumerate(crop_results):
                cropped_images.append(cropped_img)
                optimized_images.append(opt_img)
                b64 = encode_image_to_base64(opt_img)
                c_b64 = encode_image_to_base64(cropped_img)
                all_pages.append({
                    "source": "image",
                    "filename": file.filename,
                    "page": f"0_{c_idx}",
                    "image_base64": b64,
                    "cropped_base64": c_b64,
                    "blur_score": blur,
                    "is_handwritten": is_hw,
                    "doc_type": "HANDWRITTEN" if is_hw else "STANDARD"
                })
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Image error: {e}")
            raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")

    # Generate PDFs
    output_pdf = generate_pdf_from_images(cropped_images)     # User PDF: clean cropped
    debug_pdf = generate_pdf_from_images(optimized_images)    # Debug PDF: what LLM sees
    logger.info(f"Done: {len(all_pages)} page(s) optimized → ready for GPT Vision")

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "filename": file.filename,
        "file_type": ext,
        "total_pages": len(all_pages),
        "pages": all_pages,
        "output_pdf": output_pdf,
        "debug_pdf": debug_pdf
    })


# ==========================================
# MULTI-FILE ENDPOINT
# POST /api/v1/analyze-multi
# Accepts: 1-6 files (PDF/JPG/PNG mixed)
# Returns: all pages combined in one response
# ==========================================
@app.post("/api/v1/analyze-multi", tags=["OCR Pipeline"])
async def analyze_multi(
    files: List[UploadFile] = File(..., description="1-6 PDF/Image files (JPG/PNG/PDF)"),
):
    """
    Accepts 1 to 6 files: any mix of PDF and Image (JPG/PNG).
    Processes all files through the OpenCV pipeline and returns
    all optimized base64 pages combined in a single response.
    Designed for insurance dossiers: CIN recto/verso, Permis recto/verso, Carte Grise recto/verso.
    """
    if len(files) < 1 or len(files) > 6:
        raise HTTPException(status_code=400, detail=f"Expected 1-6 files, got {len(files)}")

    all_pages = []
    processed_files = []
    cropped_images = []    # Cropped-only images for user PDF
    optimized_images = []  # Fully filtered images for debug PDF

    for file in files:
        if not file.filename:
            continue

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ['pdf', 'png', 'jpg', 'jpeg']:
            raise HTTPException(status_code=400, detail=f"Unsupported file: {file.filename} (.{ext}). Accepted: pdf, jpg, jpeg, png")

        file_bytes = await file.read()
        logger.info(f"[multi] Received: {file.filename} ({len(file_bytes)//1024}KB) — type: {ext}")

        if ext == 'pdf':
            try:
                imgs = crack_pdf(file_bytes)
                for idx, img in enumerate(imgs):
                    blur, is_hw = get_image_metrics(img)
                    crop_results = optimize_for_llm_image(img, is_hw=is_hw)
                    for c_idx, (cropped_img, opt_img) in enumerate(crop_results):
                        cropped_images.append(cropped_img)
                        optimized_images.append(opt_img)
                        b64 = encode_image_to_base64(opt_img)
                        c_b64 = encode_image_to_base64(cropped_img)
                        all_pages.append({
                            "source": "pdf",
                            "filename": file.filename,
                            "page": f"{idx}_{c_idx}",
                            "image_base64": b64,
                            "cropped_base64": c_b64,
                        "blur_score": blur,
                        "is_handwritten": is_hw,
                        "doc_type": "HANDWRITTEN" if is_hw else "STANDARD"
                    })
            except Exception as e:
                logger.error(f"[multi] PDF error ({file.filename}): {e}")
                raise HTTPException(status_code=500, detail=f"PDF processing failed for {file.filename}: {str(e)}")
        else:
            try:
                img = crack_image(file_bytes)
                blur, is_hw = get_image_metrics(img)
                crop_results = optimize_for_llm_image(img, is_hw=is_hw)
                for c_idx, (cropped_img, opt_img) in enumerate(crop_results):
                    cropped_images.append(cropped_img)
                    optimized_images.append(opt_img)
                    b64 = encode_image_to_base64(opt_img)
                    c_b64 = encode_image_to_base64(cropped_img)
                    all_pages.append({
                        "source": "image",
                        "filename": file.filename,
                        "page": f"0_{c_idx}",
                        "image_base64": b64,
                        "cropped_base64": c_b64,
                    "blur_score": blur,
                    "is_handwritten": is_hw,
                    "doc_type": "HANDWRITTEN" if is_hw else "STANDARD"
                })
            except Exception as e:
                logger.error(f"[multi] Image error ({file.filename}): {e}")
                raise HTTPException(status_code=500, detail=f"Image processing failed for {file.filename}: {str(e)}")

        processed_files.append(file.filename)

    # Generate PDFs
    output_pdf = generate_pdf_from_images(cropped_images)     # User PDF: clean cropped
    debug_pdf = generate_pdf_from_images(optimized_images)    # Debug PDF: what LLM sees
    logger.info(f"[multi] Done: {len(all_pages)} page(s) from {len(processed_files)} file(s) → ready for GPT Vision")

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "filenames": processed_files,
        "total_files": len(processed_files),
        "total_pages": len(all_pages),
        "pages": all_pages,
        "output_pdf": output_pdf,
        "debug_pdf": debug_pdf
    })


# ==========================================
# BASE64 JSON ENDPOINT (for n8n Code node)
# POST /api/v1/analyze-base64
# Accepts: JSON { files: [{ filename, data, mimeType }] }
# Returns: all pages combined (same format as analyze-multi)
# ==========================================
from pydantic import BaseModel as PydanticBaseModel

class FileItem(PydanticBaseModel):
    filename: str
    data: str  # base64 encoded
    mimeType: str = "image/jpeg"

class Base64Request(PydanticBaseModel):
    files: list[FileItem]

@app.post("/api/v1/analyze-base64", tags=["OCR Pipeline"])
async def analyze_base64(req: Base64Request):
    """
    Accepts JSON with base64-encoded files.
    Designed for n8n Code nodes that cannot use require('http').
    """
    if len(req.files) < 1 or len(req.files) > 6:
        raise HTTPException(status_code=400, detail=f"Expected 1-6 files, got {len(req.files)}")

    all_pages = []
    processed_files = []
    cropped_images = []    # Cropped-only images for user PDF
    optimized_images = []  # Fully filtered images for debug PDF

    for f in req.files:
        file_bytes = base64.b64decode(f.data)
        ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
        if ext not in ['pdf', 'png', 'jpg', 'jpeg']:
            raise HTTPException(status_code=400, detail=f"Unsupported: {f.filename}")

        logger.info(f"[base64] Received: {f.filename} ({len(file_bytes)//1024}KB) — type: {ext}")

        if ext == 'pdf':
            imgs = crack_pdf(file_bytes)
            for idx, img in enumerate(imgs):
                blur, is_hw = get_image_metrics(img)
                crop_results = optimize_for_llm_image(img, is_hw=is_hw)
                for c_idx, (cropped_img, opt_img) in enumerate(crop_results):
                    cropped_images.append(cropped_img)
                    optimized_images.append(opt_img)
                    b64 = encode_image_to_base64(opt_img)
                    c_b64 = encode_image_to_base64(cropped_img)
                    all_pages.append({
                        "source": "pdf", "filename": f.filename,
                        "page": f"{idx}_{c_idx}", "image_base64": b64,
                        "cropped_base64": c_b64,
                        "blur_score": blur,
                        "is_handwritten": is_hw,
                        "doc_type": "HANDWRITTEN" if is_hw else "STANDARD"
                    })
        else:
            img = crack_image(file_bytes)
            blur, is_hw = get_image_metrics(img)
            crop_results = optimize_for_llm_image(img, is_hw=is_hw)
            for c_idx, (cropped_img, opt_img) in enumerate(crop_results):
                cropped_images.append(cropped_img)
                optimized_images.append(opt_img)
                b64 = encode_image_to_base64(opt_img)
                c_b64 = encode_image_to_base64(cropped_img)
                all_pages.append({
                    "source": "image", "filename": f.filename,
                    "page": f"0_{c_idx}", "image_base64": b64,
                    "cropped_base64": c_b64,
                    "blur_score": blur,
                    "is_handwritten": is_hw,
                    "doc_type": "HANDWRITTEN" if is_hw else "STANDARD"
                })
        processed_files.append(f.filename)

    # Generate PDFs
    output_pdf = generate_pdf_from_images(cropped_images)     # User PDF: clean cropped
    debug_pdf = generate_pdf_from_images(optimized_images)    # Debug PDF: what LLM sees
    logger.info(f"[base64] Done: {len(all_pages)} page(s) from {len(processed_files)} file(s)")

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "filenames": processed_files,
        "total_files": len(processed_files),
        "total_pages": len(all_pages),
        "pages": all_pages,
        "output_pdf": output_pdf,
        "debug_pdf": debug_pdf
    })


from typing import List

class RotatedPageItem(PydanticBaseModel):
    cropped_base64: str
    optimized_base64: str
    rotation_angle_deg: int = 0

class GenerateRotatedPdfsRequest(PydanticBaseModel):
    pages: List[RotatedPageItem]

def _decode_b64_img(b64_str: str) -> np.ndarray:
    if b64_str.startswith("data:"):
        b64_str = b64_str.split(",", 1)[1]
    nparr = np.frombuffer(base64.b64decode(b64_str), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Decoded image is None")
    return img

@app.post("/api/v1/generate-rotated-pdfs", tags=["OCR Pipeline"])
async def generate_rotated_pdfs(req: GenerateRotatedPdfsRequest):
    """
    Takes a list of base64 images and their rotation angles,
    applies the rotations, and returns final unified valid PDFs.
    """
    rotated_cropped = []
    rotated_optimized = []

    for item in req.pages:
        try:
            crop_img = _decode_b64_img(item.cropped_base64)
            opt_img = _decode_b64_img(item.optimized_base64)

            angle = item.rotation_angle_deg
            
            # Apply rotate
            crop_rot = _rotate_by_angle(crop_img, angle)
            opt_rot = _rotate_by_angle(opt_img, angle)

            rotated_cropped.append(crop_rot)
            rotated_optimized.append(opt_rot)
        except Exception as e:
            logger.error(f"Failed to process and rotate image for PDF generation: {e}")

    output_pdf = generate_pdf_from_images(rotated_cropped)
    debug_pdf = generate_pdf_from_images(rotated_optimized)

    return JSONResponse(status_code=status.HTTP_200_OK, content={
        "success": True,
        "output_pdf": output_pdf,
        "debug_pdf": debug_pdf
    })


@app.get("/health")
def health():
    return {"status": "ok", "accepts": "single file (pdf/jpg/png)", "output": "base64 images OR raw text"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
