from pathlib import Path
from typing import Optional, Union
import sys
import shutil
import json

class PathManager:
    """
    プロジェクトの主要ディレクトリ（project_root, src_dir, utils_dir）を明示的に持ち、
    それを基準に各種ファイルパスを一元管理するマネージャークラス。
    - 主要なJSONファイルはプロパティで取得可能
    - list_all_json()で全管理JSONの絶対パス一覧を取得
    - pathlib.Pathで統一
    - __file__が無い場合はbase_dir必須
    """
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
        # utils_dir: このファイルがあるディレクトリ
        self.utils_dir = Path(__file__).resolve().parent
        # src_dir: 1つ上
        self.src_dir = self.utils_dir.parent
        # project_root: さらに1つ上
        self.project_root = self.src_dir.parent
        # data_dir: src/data
        self.data_dir = self.src_dir / "data"
        # retrain_dir: src/data/retrain
        self.retrain_dir = self.data_dir / "retrain"

    @property
    def role_mapping(self) -> Path:
        return self.data_dir / "role_mapping.json"

    @property
    def image_roles(self) -> Path:
        return self.data_dir / "image_roles.json"

    @property
    def image_roles_folders(self) -> Path:
        return self.data_dir / "image_roles_folders.json"

    @property
    def last_images(self) -> Path:
        return self.data_dir / "last_images.json"

    @property
    def config(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def summary_generator_widget(self) -> Path:
        return self.data_dir / "summary_generator_widget.json"

    @property
    def image_cache_dir_config(self) -> Path:
        return self.data_dir / "image_cache_dir_path.json"

    @property
    def preset_roles(self) -> Path:
        return self.data_dir / "preset_roles.json"

    @property
    def scan_for_images_dataset(self) -> Path:
        return self.data_dir / "scan_for_images_dataset.json"

    @property
    def default_records(self) -> Path:
        return self.data_dir / "dictionaries" / "default_records.json"

    @property
    def json_files_with_description(self):
        """
        管理しているJSONファイルのパスと説明を返す
        戻り値: {key: {"path": Path, "description": str}}
        """
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
        """キャッシュディレクトリ内のJSONファイルパスを取得"""
        return self.src_dir / "image_preview_cache" / filename

    def list_all_json(self) -> list[Path]:
        """管理している全JSONファイルの絶対パスを返す（property自動検出）"""
        props = [
            attr for attr in dir(self)
            if not attr.startswith("_") and isinstance(getattr(type(self), attr, None), property)
        ]
        return [getattr(self, p) for p in props]

    def ensure_file(self, path: Union[str, Path]) -> Path:
        """ファイルの親ディレクトリを作成し、ファイルがなければ空で作る"""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.touch()
        return p

    def normalize(self, path: Union[str, Path]) -> Path:
        """パスを絶対パスに正規化"""
        return Path(path).expanduser().resolve()

    def copy_all_managed_files(self, dest_dir: Union[str, Path], overwrite: bool = True):
        """
        管理している全ファイル・ディレクトリを指定ディレクトリに一括コピーする
        :param dest_dir: コピー先ディレクトリ
        :param overwrite: 既存ファイルを上書きするか
        """
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        # JSONファイル群
        for src_path in self.list_all_json():
            if src_path.exists():
                dst_path = dest_dir / src_path.name
                if dst_path.exists() and not overwrite:
                    continue
                shutil.copy2(src_path, dst_path)
        # image_preview_cache ディレクトリ（キャッシュ）
        cache_dir = self.src_dir / "image_preview_cache"
        if cache_dir.exists() and cache_dir.is_dir():
            dst_cache_dir = dest_dir / "image_preview_cache"
            if dst_cache_dir.exists() and overwrite:
                shutil.rmtree(dst_cache_dir)
            if not dst_cache_dir.exists():
                shutil.copytree(cache_dir, dst_cache_dir)
        # data/dictionaries ディレクトリ
        dict_dir = self.project_root / "data" / "dictionaries"
        if dict_dir.exists() and dict_dir.is_dir():
            dst_dict_dir = dest_dir / "dictionaries"
            if dst_dict_dir.exists() and overwrite:
                shutil.rmtree(dst_dict_dir)
            if not dst_dict_dir.exists():
                shutil.copytree(dict_dir, dst_dict_dir)
        # 必要に応じて他の管理ディレクトリも追加

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
    def model_search_dirs(self) -> list[Path]:
        """
        YOLOモデル探索用のディレクトリリストを返す。
        src/datasets と src/yolo のみ。
        存在するもののみ返す。
        """
        dirs = [
            self.project_root / "src" / "datasets",
            self.project_root / "src" / "yolo",
        ]
        return [d for d in dirs if d.exists() and d.is_dir()]
    
    def set_last_json_path(self, path: Union[str, Path]):
        """
        最後に開いた画像リストJSONパスをconfig.jsonに保存
        """
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
        """
        config.jsonから最後に開いた画像リストJSONパスを取得
        """
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
        """
        現在有効な画像リストJSONパス（config.jsonのlast_json_path優先、なければデフォルト）
        """
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
        """
        現在有効な画像リストJSONパスをconfig.jsonに保存
        """
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

    @property
    def image_preview_cache_master(self) -> Path:
        return self.data_dir / "image_preview_cache_master.json"

    @property
    def image_cache_dir(self) -> Path:
        return self.src_dir / "image_preview_cache"

    def get_retrain_data_dir(self) -> Path:
        """再学習用データディレクトリのパスを取得"""
        return self.retrain_dir

    @property
    def yolo_db(self) -> Path:
        """YOLO用DBファイル（yolo_data.db）の絶対パスを返す"""
        return self.project_root / "yolo_data.db"

# グローバルインスタンス
path_manager = PathManager()