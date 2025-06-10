# --- Copied from src/scan_for_images_dataset.py ---
# utils/配下に移動したため、importは from summarygenerator.utils. で参照
import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
from summarygenerator.utils import CustomImage, CustomPDF, CustomDocx

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_images_from_pdf(pdf_path: str) -> List[CustomImage]:
    """
    Extract images from a PDF file.
    """
    logger.info(f"Extracting images from PDF: {pdf_path}")
    images = []
    try:
        # PDFを画像に変換
        pages = convert_from_path(pdf_path, dpi=300)
        for page_number, page in enumerate(pages):
            # 各ページを画像として保存
            image_path = f"{pdf_path}_page_{page_number + 1}.jpg"
            page.save(image_path, "JPEG")
            images.append(CustomImage(image_path, "JPEG"))
            logger.info(f"Saved image: {image_path}")
    except Exception as e:
        logger.error(f"Error extracting images from PDF: {e}")
    return images

def extract_images_from_docx(docx_path: str) -> List[CustomImage]:
    """
    Extract images from a DOCX file.
    """
    logger.info(f"Extracting images from DOCX: {docx_path}")
    images = []
    try:
        docx = CustomDocx(docx_path)
        for rel in docx.package.rels.values():
            if "image" in rel.target_ref:
                # 画像を抽出
                image = rel.target_part.blob
                image_path = f"{docx_path}_{rel.target_ref.split('/')[-1]}"
                with open(image_path, "wb") as f:
                    f.write(image)
                images.append(CustomImage(image_path, rel.target_ref.split('.')[-1]))
                logger.info(f"Saved image: {image_path}")
    except Exception as e:
        logger.error(f"Error extracting images from DOCX: {e}")
    return images

def extract_images_from_txt(txt_path: str) -> List[CustomImage]:
    """
    Extract images from a TXT file (assuming images are base64 encoded).
    """
    logger.info(f"Extracting images from TXT: {txt_path}")
    images = []
    try:
        with open(txt_path, "r") as f:
            content = f.read()
            # Base64 画像データを正規表現で抽出
            image_data_list = re.findall(r"data:image/(png|jpg|jpeg);base64,([A-Za-z0-9+/=]+)", content)
            for i, (img_type, img_data) in enumerate(image_data_list):
                # 画像データをデコードして保存
                image_path = f"{txt_path}_image_{i + 1}.{img_type}"
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data.encode())
                images.append(CustomImage(image_path, img_type))
                logger.info(f"Saved image: {image_path}")
    except Exception as e:
        logger.error(f"Error extracting images from TXT: {e}")
    return images

def extract_images_from_html(html_path: str) -> List[CustomImage]:
    """
    Extract images from an HTML file.
    """
    logger.info(f"Extracting images from HTML: {html_path}")
    images = []
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            # 画像のURLを正規表現で抽出
            img_urls = re.findall(r"<img [^>]*src=['\"]([^'\"]+)['\"][^>]*>", content)
            for i, img_url in enumerate(img_urls):
                # 画像をダウンロードして保存
                img_data = requests.get(img_url).content
                image_path = f"{html_path}_image_{i + 1}.jpg"
                with open(image_path, "wb") as img_file:
                    img_file.write(img_data)
                images.append(CustomImage(image_path, "JPEG"))
                logger.info(f"Saved image: {image_path}")
    except Exception as e:
        logger.error(f"Error extracting images from HTML: {e}")
    return images

def extract_images(file_path: str) -> List[CustomImage]:
    """
    Extract images from a file (PDF, DOCX, TXT, HTML).
    """
    logger.info(f"Extracting images from file: {file_path}")
    ext = file_path.split('.')[-1].lower()
    if ext == "pdf":
        return extract_images_from_pdf(file_path)
    elif ext == "docx":
        return extract_images_from_docx(file_path)
    elif ext == "txt":
        return extract_images_from_txt(file_path)
    elif ext in ["html", "htm"]:
        return extract_images_from_html(file_path)
    else:
        logger.warning(f"Unsupported file type: {ext}")
        return []

def main(file_paths: List[str]):
    all_images = []
    for file_path in file_paths:
        images = extract_images(file_path)
        all_images.extend(images)
    logger.info(f"Extracted {len(all_images)} images from {len(file_paths)} files.")

# if __name__ == "__main__":
#     import sys
#     file_paths = sys.argv[1:]
#     main(file_paths)
