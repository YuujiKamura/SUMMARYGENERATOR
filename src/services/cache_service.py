from pathlib import Path
from src.widgets.image_preview_utils import save_image_cache_with_location
from src.utils.image_cache_utils import get_image_cache_path
import json
import os
from src import db_manager

class CacheService:
    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or os.getenv("IMAGE_CACHE_DIR", "image_preview_cache"))

    def get_cache_path(self, img_path: str | Path) -> Path:
        img_name = Path(img_path).stem + ".json"
        return self.base_dir / img_name

    def load_location_from_cache(self, img_path) -> str | None:
        p = self.get_cache_path(img_path)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("location")
        except (OSError, json.JSONDecodeError):
            return None

    def save_bboxes_with_location(self, img_path, bboxes, location, _dir=None) -> bool:
        p = self.get_cache_path(img_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({
                "bboxes": [b.model_dump() for b in bboxes],
                "location": location
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False

    def save_location(self, img_path, location) -> bool:
        p = self.get_cache_path(img_path)
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
            else:
                data = {}
            data["location"] = location
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            # DB 更新
            try:
                db_manager.ImageManager.add_image(Path(img_path).name, str(img_path), location=location)
            except Exception:
                pass
            return True
        except OSError:
            return False
