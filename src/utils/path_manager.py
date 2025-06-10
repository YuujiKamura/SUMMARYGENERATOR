# --- 要件定義・データ配置ガイド ---
# 本パスマネージャーは「summarygenerator」配下での運用を前提とする。
# 管理対象データの主な配置ルール：
# ・画像ファイル本体：Googleドライブやローカル任意パス（例: H:\マイドライブ\...\RIMG8603.JPG）
# ・個別画像JSON：src/image_preview_cache/xxxx.json（xxxxは画像パスのMD5ハッシュ）
#   ※ summarygenerator/image_preview_cache/ は現状使わない
# ・マスタ画像リストJSON：summarygenerator/datasets/yolo_dataset_YYYYMMDD/master_image_list.json
# ・YOLOデータセット：summarygenerator/datasets/yolo_dataset_YYYYMMDD/
# ・各種設定/辞書/ロール情報：summarygenerator/data/ や summarygenerator/ 配下
#
# 画像パス→個別JSONの対応は「画像パスのMD5ハッシュ値でファイル名を生成し、src/image_preview_cache配下に格納」することで一意にマッピングする。
#
# パスマネージャーはsrc/image_preview_cacheのみをキャッシュディレクトリとして管理する。
# 必要に応じてadd_image_cache_dirで他ディレクトリも追加可能。
#
# 迷った場合はこのコメントを参照すること。

# --- Copied from src/utils/path_manager.py ---
from pathlib import Path
from typing import Optional, Union
import sys
import shutil
import json

class PathManager:
    _instance = None
    def __new__(cls, base_dir: Optional[Union[str, Path]] = None, write_protect: bool = False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    def __init__(self, base_dir: Optional[Union[str, Path]] = None, write_protect: bool = False):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.write_protect = write_protect
        self._init_paths(base_dir)
    def _init_paths(self, base_dir: Optional[Union[str, Path]]):
        self.utils_dir = Path(__file__).resolve().parent
        self.project_root = self.utils_dir.parent
        self.src_dir = self.project_root
        # 管理するキャッシュディレクトリリスト（親ディレクトリ名: 絶対パス）
        self.image_cache_dirs = {}
        # src/image_preview_cacheのみ登録（存在すれば）
        src_cache = (self.project_root.parent / "src" / "image_preview_cache").resolve()
        if src_cache.exists():
            self.image_cache_dirs["src"] = src_cache

    def add_image_cache_dir(self, name: str, path: Union[str, Path]):
        """
        任意のキャッシュディレクトリを管理対象に追加
        """
        self.image_cache_dirs[name] = Path(path).resolve()

    @property
    def role_mapping(self) -> Path:
        """
        summarygenerator/data/role_mapping.json（なければdata/role_mapping.json）
        """
        p = (self.project_root / "data" / "role_mapping.json").resolve()
        if p.exists():
            return p
        # fallback: ルートdata/role_mapping.json
        fallback = (self.project_root.parent / "data" / "role_mapping.json").resolve()
        return fallback

    @property
    def image_roles(self) -> Path:
        return (self.project_root / "image_roles.json").resolve()
    @property
    def image_roles_folders(self) -> Path:
        return (self.project_root / "image_roles_folders.json").resolve()
    @property
    def last_images(self) -> Path:
        return (self.project_root / "last_images.json").resolve()
    @property
    def config(self) -> Path:
        """
        config.jsonはsummarygenerator/config.json優先、なければプロジェクトルートのconfig.jsonを使う。
        """
        p = (self.project_root / "summarygenerator" / "config.json").resolve()
        if p.exists():
            return p
        return (self.project_root / "config.json").resolve()
    @property
    def summary_generator_widget(self) -> Path:
        return (self.src_dir / "summary_generator_widget.json").resolve()
    @property
    def image_cache_dir_config(self) -> Path:
        return (self.utils_dir / "image_cache_dir_path.json").resolve()
    @property
    def preset_roles(self) -> Path:
        """
        summarygenerator/data/preset_roles.json（なければdata/preset_roles.json）
        """
        p = (self.project_root / "data" / "preset_roles.json").resolve()
        if p.exists():
            return p
        fallback = (self.project_root.parent / "data" / "preset_roles.json").resolve()
        return fallback
    @property
    def scan_for_images_dataset(self) -> Path:
        return (self.src_dir / "scan_for_images_dataset.json").resolve()
    @property
    def default_records(self) -> Path:
        """
        summarygenerator/data/dictionaries/default_records.json（なければdata/dictionaries/default_records.json）
        """
        p = (self.project_root / "data" / "dictionaries" / "default_records.json").resolve()
        if p.exists():
            return p
        fallback = (self.project_root.parent / "data" / "dictionaries" / "default_records.json").resolve()
        return fallback
    @property
    def json_files_with_description(self):
        return {
            "image_list": {
                "path": self.scan_for_images_dataset,
                "description": "プロジェクトの画像リスト（YOLOデータセットの元）"
            },
            "role_mapping": {
                "path": self.role_mapping,
                "description": "ロール対応表"
            },
            "image_roles": {
                "path": self.image_roles,
                "description": "画像ごとのロール情報（アノテーション）"
            },
            "image_roles_folders": {
                "path": self.image_roles_folders,
                "description": "フォルダ単位のロール情報"
            },
            "last_images": {
                "path": self.last_images,
                "description": "直近の画像リスト"
            },
            "config": {
                "path": self.config,
                "description": "アプリ全体の設定ファイル"
            },
            "summary_generator_widget": {
                "path": self.summary_generator_widget,
                "description": "サマリー生成ウィジェットの設定"
            },
            "image_cache_dir_config": {
                "path": self.image_cache_dir_config,
                "description": "画像キャッシュディレクトリ設定"
            },
            "preset_roles": {
                "path": self.preset_roles,
                "description": "プリセットロール定義"
            },
            "default_records": {
                "path": self.default_records,
                "description": "デフォルトの分類辞書"
            },
        }
    def get_json_files_with_description(self):
        return self.json_files_with_description
    def get_cache_json(self, filename: str) -> Path:
        return self.src_dir / "image_preview_cache" / filename
    def list_all_json(self) -> list[Path]:
        props = [
            attr for attr in dir(self)
            if not attr.startswith("_") and isinstance(getattr(type(self), attr, None), property)
        ]
        return [getattr(self, p) for p in props]
    def ensure_file(self, path: Union[str, Path]) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.touch()
        return p
    def normalize(self, path: Union[str, Path]) -> Path:
        return Path(path).expanduser().resolve()
    def copy_all_managed_files(self, dest_dir: Union[str, Path], overwrite: bool = True):
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        for src_path in self.list_all_json():
            if src_path.exists():
                dst_path = dest_dir / src_path.name
                if dst_path.exists() and not overwrite:
                    continue
                shutil.copy2(src_path, dst_path)
        cache_dir = self.src_dir / "image_preview_cache"
        if cache_dir.exists() and cache_dir.is_dir():
            dst_cache_dir = dest_dir / "image_preview_cache"
            if dst_cache_dir.exists() and overwrite:
                shutil.rmtree(dst_cache_dir)
            if not dst_cache_dir.exists():
                shutil.copytree(cache_dir, dst_cache_dir)
        dict_dir = self.project_root / "data" / "dictionaries"
        if dict_dir.exists() and dict_dir.is_dir():
            dst_dict_dir = dest_dir / "dictionaries"
            if dst_dict_dir.exists() and overwrite:
                shutil.rmtree(dst_dict_dir)
            if not dst_dict_dir.exists():
                shutil.copytree(dict_dir, dst_dict_dir)
    @property
    def yolo_model_dir(self) -> Path:
        return self.project_root / "yolo"
    @property
    def yolov8n(self) -> Path:
        return self.yolo_model_dir / "yolov8n.pt"
    @property
    def yolov8s(self) -> Path:
        return self.yolo_model_dir / "yolov8s.pt"
    @property
    def yolo11n(self) -> Path:
        return self.yolo_model_dir / "yolo11n.pt"
    @property
    def models_dir(self) -> Path:
        return self.project_root / "models"
    def set_last_json_path(self, path: Union[str, Path]):
        if getattr(self, 'write_protect', False):
            return
        config_path = self.config
        config = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["last_json_path"] = str(path)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    def get_last_json_path(self) -> str:
        config_path = self.config
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("last_json_path", str(self.scan_for_images_dataset))
            except Exception:
                return str(self.scan_for_images_dataset)
        return str(self.scan_for_images_dataset)
    @property
    def current_image_list_json(self) -> str:
        config_path = self.config
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                return config.get("last_json_path", str(self.scan_for_images_dataset))
            except Exception:
                return str(self.scan_for_images_dataset)
        return str(self.scan_for_images_dataset)
    @current_image_list_json.setter
    def current_image_list_json(self, path: Union[str, Path]):
        if getattr(self, 'write_protect', False):
            return
        config_path = self.config
        config = {}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        config["last_json_path"] = str(path)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    def get_yolo_dataset_dir(self, date_str: Optional[str] = None) -> Optional[Path]:
        """
        YOLOデータセットディレクトリのパスを取得（例: summarygenerator/datasets/yolo_dataset_YYYYMMDD）
        date_str未指定時は最新日付を自動検出
        """
        base_dir = self.project_root / "datasets"
        if date_str:
            return base_dir / f"yolo_dataset_{date_str}"
        # 未指定時は最新
        if not base_dir.exists():
            return None
        date_dirs = sorted([d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("yolo_dataset_")], reverse=True)
        return date_dirs[0] if date_dirs else None

    @property
    def master_image_list_json(self) -> Optional[Path]:
        """
        YOLO分類用マスタ画像リストJSONのパス（例: summarygenerator/datasets/yolo_dataset_YYYYMMDD/master_image_list.json）
        デフォルトは最新日付ディレクトリを自動検出、なければNone
        """
        base_dir = self.project_root / "datasets"
        if not base_dir.exists():
            return None
        date_dirs = sorted([d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("yolo_dataset_")], reverse=True)
        for d in date_dirs:
            candidate = d / "master_image_list.json"
            if candidate.exists():
                return candidate
        return None

    def get_individual_json_path(self, image_path: Union[str, Path], cache_dir_name: Optional[str] = None) -> Path:
        """
        画像パスから個別画像JSONのキャッシュパスを絶対パスで返す。
        src/image_preview_cache配下を常に使う。
        """
        import hashlib
        image_path = str(image_path)
        hash_name = hashlib.md5(image_path.encode('utf-8')).hexdigest()
        base = self.src_dir / "image_preview_cache"
        return base / f"{hash_name}.json"

    def find_existing_individual_json(self, image_path: Union[str, Path]) -> Optional[Path]:
        """
        画像パスから、管理している全キャッシュディレクトリを逆探索し、
        実際に存在する個別画像JSONの絶対パスを返す（なければNone）。
        """
        import hashlib
        image_path = str(image_path)
        hash_name = hashlib.md5(image_path.encode('utf-8')).hexdigest()
        for base in self.image_cache_dirs.values():
            candidate = (base / f"{hash_name}.json").resolve()
            if candidate.exists():
                return candidate
        return None
    @property
    def image_cache_dir(self) -> Path:
        """
        個別画像キャッシュディレクトリの絶対パスを返す（src/image_preview_cacheをデフォルトとする）
        """
        return Path(__file__).parent.parent / "image_preview_cache"
path_manager = PathManager()
