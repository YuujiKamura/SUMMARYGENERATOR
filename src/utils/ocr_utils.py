from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance
from paddleocr import PaddleOCR

def extract_texts_from_clips(
    img_path: str,
    detections: List[Dict[str, Any]],
    lang: str = "japan",
    use_gpu: bool = False,
    contrast: float = 2.0,
    ocr_instance: Optional[PaddleOCR] = None
) -> Dict[int, List[str]]:
    """
    Extract OCR texts from specified clipping regions of an image.

    Args:
        img_path: Path to the source image file.
        detections: A list of dicts, each containing an 'xyxy' key with
                    [x1, y1, x2, y2] pixel coordinates of the clip.
        lang: Language code for PaddleOCR (e.g., 'japan', 'en').
        use_gpu: Whether to enable GPU acceleration in PaddleOCR.
        contrast: Contrast enhancement factor applied before OCR.
        ocr_instance: An existing PaddleOCR instance to reuse. If None,
                      a new one will be created.

    Returns:
        A dictionary mapping each detection index to a list of detected texts.
    """
    # Verify image exists
    image_file = Path(img_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file not found: {img_path}")

    # Open and preprocess image (grayscale + contrast + RGB)
    image = Image.open(image_file).convert("L")
    if contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(contrast)
    image_rgb = image.convert("RGB")

    # Initialize PaddleOCR if needed
    if ocr_instance is None:
        ocr_instance = PaddleOCR(
            use_gpu=use_gpu,
            lang=lang,
            det=False,  # no internal detection
            rec=True,
            cls=False
        )

    results: Dict[int, List[str]] = {}

    for idx, det in enumerate(detections):
        xy = det.get("xyxy")
        if not xy or len(xy) != 4:
            results[idx] = []
            continue

        # Crop region
        x1, y1, x2, y2 = map(int, xy)
        clip = image_rgb.crop((x1, y1, x2, y2))
        clip_np = np.asarray(clip)

        # Perform OCR on the clip
        ocr_res = ocr_instance.ocr(
            clip_np,
            det=False,
            rec=True,
            cls=False
        )

        # Extract text strings
        texts: List[str] = []
        if ocr_res and len(ocr_res) > 0:
            for entry in ocr_res[0]:
                text, _ = entry[1]
                texts.append(text)

        results[idx] = texts

    return results
