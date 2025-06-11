from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QStyledItemDelegate, QListView, QAbstractItemView, QDialog, QTextEdit, QProgressBar, QCheckBox
from PyQt6.QtGui import QIcon, QPainter, QPen, QColor
from .scan_for_images_widget import ScanForImagesWidget
from widgets.role_list_widget import RoleListWidget
from PyQt6.QtCore import Qt, QPoint, QSize, QAbstractListModel, QModelIndex, QRect, QVariant, QEvent
from PyQt6.QtGui import QPixmap
import os
import json
import threading
import glob
from PIL import Image
from utils.model_manager import ModelManager
from utils.image_utils import scan_folder_for_valid_images
from pathlib import Path
# from exporters.yolo_export import export_to_yolo
from models import Annotation, ClassDefinition, AnnotationDataset, BoundingBox
from src.utils import io_utils
import textwrap
import shutil

# --- ロール割当JSON→AnnotationDataset変換関数 ---
def convert_role_json_to_annotation_dataset(json_paths, copy_network_drive=True, skip_missing_files=True, use_temp_dir=True):
    # クラス名・IDの一意リスト作成
    class_name_to_id = {}
    class_defs = []
    annotations = {}
    
    # パス正規化のためのマッピング辞書
    path_mapping = {}
    
    # デバッグ用変数
    total_images = 0
    total_annotations = 0
    failures = 0
    
    # ローカルにコピーした一時ファイルのリスト
    temp_files = []
    
    # 一時ファイルディレクトリの作成
    import tempfile
    temp_dir = os.path.join(tempfile.gettempdir(), "photocategorizer_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # ネットワークドライブパスのチェック
    def is_network_drive_path(path):
        return (path.startswith(("H:", "H:\\")) or 
                "マイドライブ" in path or 
                "Googleドライブ" in path or
                "\\\\nas" in path or
                "\\\\server" in path)
    
    # ファイル名から拡張子を取得
    def get_extension(file_path):
        return os.path.splitext(file_path)[1].lower()
    
    # 画像ファイルをローカルにコピー
    def copy_to_local(img_path):
        try:
            # 画像ファイルが存在するか確認
            if not os.path.exists(img_path):
                print(f"画像が存在しません: {img_path}")
                return None
                
            # ファイル名（衝突を避けるためにハッシュ値を追加）
            import hashlib
            file_hash = hashlib.md5(img_path.encode()).hexdigest()[:8]
            basename = os.path.basename(img_path)
            temp_path = os.path.join(temp_dir, f"{file_hash}_{basename}")
            
            # 既存の一時ファイルならそれを返す
            if os.path.exists(temp_path):
                return temp_path
                
            # コピー実行
            shutil.copy2(img_path, temp_path)
            temp_files.append(temp_path)
            print(f"ネットワークドライブからコピー: {img_path} -> {temp_path}")
            return temp_path
        except Exception as e:
            print(f"ファイルコピーエラー: {img_path} - {e}")
            return None
    
    # WindowsパスをPython形式に標準化する関数
    def normalize_path(img_path):
        """パスを正規化して一貫した形式にする"""
        try:
            # 既に正規化済みのパスがあればそれを使用
            if img_path in path_mapping:
                return path_mapping[img_path]
                
            # ネットワークドライブのパスの場合、コピーオプションが有効ならローカルにコピー
            if copy_network_drive and is_network_drive_path(img_path):
                # ローカルにコピーして新しいパスを返す
                local_path = copy_to_local(img_path)
                if local_path:
                    path_mapping[img_path] = local_path
                    return local_path
                elif skip_missing_files:
                    # コピー失敗＆スキップ設定なら、無効なパスとしてマーク
                    path_mapping[img_path] = None
                    return None
            
            # 日本語パスの場合、常にローカルコピーを使用（文字化け対策）
            if use_temp_dir and not is_network_drive_path(img_path) and os.path.exists(img_path):
                # パスエンコーディングに問題がある可能性があるファイルを全て一時ディレクトリにコピー
                local_path = copy_to_local(img_path)
                if local_path:
                    path_mapping[img_path] = local_path
                    return local_path
            
            # ファイルが存在するか確認（スキップオプション有効時）
            if skip_missing_files and not os.path.exists(img_path):
                alt_path = img_path.replace('\\', '/')
                if not os.path.exists(alt_path):
                    path_mapping[img_path] = None
                    return None
                # スラッシュ変換したパスが存在する場合
                img_path = alt_path
            
            # マッピングにない場合、正規化を試みる    
            try:
                # Windowsパスのバックスラッシュをフォワードスラッシュに変換
                norm_path = img_path.replace('\\', '/')
                # 存在確認
                if not os.path.exists(norm_path) and os.path.exists(img_path):
                    norm_path = img_path
                
                # 絶対パスに変換
                p = Path(norm_path).resolve()
                abs_path = str(p)
                
                # ファイルが存在するか確認（存在すれば正規化に成功）
                if os.path.exists(abs_path):
                    # ファイルパスに日本語が含まれる場合は一時ディレクトリにコピー
                    if use_temp_dir:
                        local_path = copy_to_local(abs_path)
                        if local_path:
                            path_mapping[img_path] = local_path
                            return local_path
                    
                    path_mapping[img_path] = abs_path
                    return abs_path
                
                # 元のパスで存在確認
                if os.path.exists(img_path):
                    if use_temp_dir:
                        local_path = copy_to_local(img_path)
                        if local_path:
                            path_mapping[img_path] = local_path
                            return local_path
                    
                    path_mapping[img_path] = img_path
                    return img_path
                
                # どちらも存在しない場合、最初の値を使用
                path_mapping[img_path] = norm_path
                return norm_path
            except Exception as e:
                print(f"パス正規化エラー: {img_path} - {e}")
                path_mapping[img_path] = img_path
                return img_path
        except Exception as e:
            print(f"パス処理例外: {img_path} - {e}")
            return img_path
    
    # JSONファイルごとに処理
    for json_path in json_paths:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            label = data.get('label', Path(json_path).stem)
            if label not in class_name_to_id:
                cid = len(class_name_to_id)
                class_name_to_id[label] = cid
                class_defs.append(ClassDefinition(id=cid, name=label, color="#FF0000"))
            cid = class_name_to_id[label]
            
            # 画像の処理
            for img in data.get('images', []):
                total_images += 1
                
                # 画像パスを取得（文字列 or 辞書のpath）
                try:
                    if isinstance(img, str):
                        img_path = img
                        bboxes = []
                    else:
                        img_path = img['path']
                        bboxes = img.get('bboxes', [])
                    
                    # パスを正規化
                    norm_img_path = normalize_path(img_path)
                    
                    # 無効なパス（正規化に失敗）ならスキップ
                    if norm_img_path is None:
                        print(f"無効なパスをスキップ: {img_path}")
                        failures += 1
                        continue
                    
                    # アノテーションが無い場合はスキップ
                    if not bboxes:
                        print(f"バウンディングボックスなし: {norm_img_path}")
                        failures += 1
                        continue
                    
                    # 既存のアノテーションを取得または初期化
                    anns = []
                    for i, bbox in enumerate(bboxes):
                        try:
                            box = BoundingBox(
                                x1=float(bbox['bbox'][0]), y1=float(bbox['bbox'][1]),
                                x2=float(bbox['bbox'][2]), y2=float(bbox['bbox'][3])
                            )
                            anns.append(Annotation(id=i, class_id=cid, box=box))
                            total_annotations += 1
                        except (KeyError, IndexError, ValueError, TypeError) as e:
                            print(f"バウンディングボックス形式エラー: {e}")
                            failures += 1
                            continue
                    
                    # アノテーションがなければスキップ
                    if not anns:
                        print(f"有効なアノテーションがなし: {norm_img_path}")
                        failures += 1
                        continue
                    
                    # 画像が存在するか確認
                    if not os.path.exists(norm_img_path) and not os.path.exists(img_path):
                        if skip_missing_files:
                            print(f"画像ファイルが存在しない: {norm_img_path}")
                            failures += 1
                            continue
                    
                    # 正規化したパスとオリジナルパスの両方をチェック
                    if norm_img_path not in annotations and img_path not in annotations:
                        annotations[norm_img_path] = anns
                    else:
                        # すでに存在するなら使用されているキーを特定
                        existing_key = norm_img_path if norm_img_path in annotations else img_path
                        # 同一画像の追加アノテーションを既存のリストに追加
                        # 重複IDを避けるためにオフセットを計算
                        offset = len(annotations[existing_key])
                        for i, ann in enumerate(anns):
                            annotations[existing_key].append(
                                Annotation(id=offset+i, class_id=ann.class_id, box=ann.box)
                            )
                except Exception as e:
                    print(f"画像エントリ処理エラー: {img} - {e}")
                    failures += 1
                    continue
                    
        except Exception as e:
            print(f"JSONファイル処理エラー: {json_path} - {e}")
            failures += 1
    
    print(f"変換統計: 総画像数={total_images}, 成功={len(annotations)}, 失敗={failures}, アノテーション={total_annotations}")
    
    # 処理完了後、必要に応じて一時ファイルを削除（オプション）
    # for temp_file in temp_files:
    #     try:
    #         if os.path.exists(temp_file):
    #             os.remove(temp_file)
    #     except Exception as e:
    #         print(f"一時ファイルの削除に失敗: {temp_file} - {e}")
    
    return AnnotationDataset(classes=class_defs, annotations=annotations)

class DetectResultWidget(QWidget):
    def __init__(self, parent=None, test_mode=False, save_dir="seeds"):
        super().__init__(parent)
        self.setWindowTitle("DetectResultWidget - detect_result_widget.py")
        layout = QHBoxLayout(self)
        # --- ロールリスト（左）: プリセットJSONを常に使う ---
        preset_roles_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/preset_roles.json'))
        self.role_list = RoleListWidget(preset_file=preset_roles_path, save_dir=save_dir)
        layout.addWidget(self.role_list)
        # サムネイル一覧＋割り当てボタン（右）
        vbox = QVBoxLayout()
        vbox.addWidget(QLabel("検出画像一覧"))
        self.image_widget = ScanForImagesWidget()
        vbox.addWidget(self.image_widget, 1)
        self.image_paths = []
        self.bbox_dict = {}
        self.assign_btn = QPushButton("選択画像をロールに割り当て")
        self.assign_btn.clicked.connect(self.assign_selected_images)
        vbox.addWidget(self.assign_btn)
        self.reassign_btn = QPushButton("bboxなし画像の再検出・上書き")
        self.reassign_btn.clicked.connect(self.show_reassign_dialog)
        vbox.addWidget(self.reassign_btn)
        self.export_yolo_btn = QPushButton("YOLOエクスポート")
        self.export_yolo_btn.clicked.connect(self.export_yolo_from_roles)
        vbox.addWidget(self.export_yolo_btn)
        # --- 検出結果テキスト表示欄を追加 ---
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        vbox.addWidget(QLabel("検出結果テキスト"))
        vbox.addWidget(self.result_text)
        layout.addLayout(vbox, 1)
        self.setLayout(layout)
        self.assignment = {}
        self.test_mode = test_mode
        self.save_dir = save_dir
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../logs")
        logs_dir = os.path.abspath(logs_dir)
        os.makedirs(logs_dir, exist_ok=True)
        self._settings_path = os.path.join(logs_dir, "detect_result_widget_settings.json")
        self.restore_window_settings()
        if not hasattr(self, '_restored_size') or not self._restored_size:
            self.resize(1200, 800)
        mainwin = self.window()
        if hasattr(mainwin, 'set_current_widget_name'):
            mainwin.set_current_widget_name("detect_result_widget.py")

    def set_images(self, image_paths, bbox_dict=None):
        print("[set_images] image_paths:", image_paths)
        self.image_paths = image_paths
        self.bbox_dict = bbox_dict or {}
        self.image_widget.set_images(image_paths)
        # 最初の画像の検出結果を表示
        if image_paths:
            self.show_detection_text(image_paths[0])
        # 画像選択時に検出結果テキストを更新
        if hasattr(self.image_widget, 'fast_thumb_list'):
            sel_model = self.image_widget.fast_thumb_list.selectionModel()
            if sel_model:
                sel_model.selectionChanged.connect(self.on_image_selection_changed)

    def on_image_selection_changed(self):
        selected = self.image_widget.get_selected_image_paths()
        if selected:
            self.show_detection_text(selected[0])

    def show_detection_text(self, img_path):
        dets = self.bbox_dict.get(img_path, [])
        if not dets:
            self.result_text.setText("検出結果なし")
            return
        lines = []
        for det in dets:
            # det: {'bbox': [...], 'class_name': ..., 'confidence': ...}
            bbox = det.get('bbox', [])
            cname = det.get('class_name', '')
            conf = det.get('confidence', 0)
            lines.append(f"{cname} conf={conf:.2f} bbox={bbox}")
        self.result_text.setText("\n".join(lines))

    def assign_selected_images(self):
        selected_paths = self.image_widget.get_selected_image_paths()
        if not selected_paths:
            return
        role_items = self.role_list.list_widget.selectedItems()
        if not role_items:
            return
        role_label = role_items[0].data(Qt.ItemDataRole.UserRole)
        for path in selected_paths:
            self.assignment[path] = role_label
        if self.test_mode:
            self.save_to_json(role_label, selected_paths)
            self.role_list.update_entry_counts()
        else:
            threading.Thread(target=self._save_and_update, args=(role_label, selected_paths), daemon=True).start()

    def _save_and_update(self, role_label, img_paths):
        self.save_to_json(role_label, img_paths)
        self.role_list.update_entry_counts()

    def save_to_json(self, role_label, img_paths):
        os.makedirs(self.save_dir, exist_ok=True)
        json_path = os.path.join(self.save_dir, f"{role_label}.json")
        # 既存データの読み込み
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                images = {img['path']: img for img in data.get("images", [])}
            except Exception:
                images = {}
        else:
            images = {}
        # bbox_dictからバウンディングボックス情報を取得
        bbox_dict = getattr(self.image_widget, 'bbox_dict', {})
        for path in img_paths:
            bboxes = []
            if bbox_dict and path in bbox_dict:
                for cid, cname, conf, xyxy in bbox_dict[path]:
                    if xyxy:
                        bboxes.append({
                            "class_id": cid,
                            "bbox": list(map(float, xyxy)),
                            "confidence": float(conf)
                        })
            # 既存データを上書き/追加
            images[path] = {"path": path, "bboxes": bboxes}
        out = {"label": role_label, "images": list(images.values())}
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

    def restore_window_settings(self):
        try:
            if os.path.exists(self._settings_path):
                import json
                with open(self._settings_path, "r", encoding="utf-8") as f:
                    s = json.load(f)
                if "size" in s:
                    self.resize(*s["size"])
                    self._restored_size = True
                if "pos" in s:
                    self.move(*s["pos"])
        except Exception:
            pass

    def save_window_settings(self):
        s = {
            "size": [self.width(), self.height()],
            "pos": [self.x(), self.y()]
        }
        with open(self._settings_path, "w", encoding="utf-8") as f:
            import json
            json.dump(s, f, ensure_ascii=False, indent=2)

    def find_images_without_bboxes(self):
        """
        seedsディレクトリ配下の全ロールJSONを走査し、bbox情報がない画像パスをロールごとにリストアップする。
        戻り値: {role_label: [image_path, ...], ...}
        """
        result = {}
        for fname in os.listdir(self.save_dir):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(self.save_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                label = data.get('label', fname.replace('.json', ''))
                images = data.get('images', [])
                no_bbox = []
                for entry in images:
                    if isinstance(entry, str):
                        no_bbox.append(entry)
                    elif isinstance(entry, dict):
                        bboxes = entry.get('bboxes', None)
                        if not bboxes:
                            no_bbox.append(entry.get('path'))
                if no_bbox:
                    result[label] = no_bbox
            except Exception as e:
                print(f"Error reading {path}: {e}")
        return result

    def show_reassign_dialog(self):
        """
        bboxなし画像の再検出・上書きフローを開始するUIダイアログを表示
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox
        # 1. bboxなし画像を抽出
        no_bbox_dict = self.find_images_without_bboxes()
        all_images = []
        for imgs in no_bbox_dict.values():
            all_images.extend(imgs)
        if not all_images:
            QMessageBox.information(self, "情報", "全ての画像にバウンディングボックスがあります。")
            return
        # 2. モデル＆ラベル選択UI
        dlg = QDialog(self)
        dlg.setWindowTitle("YOLOラベル再検出でbbox補完 - detect_result_widget.py")
        vbox = QVBoxLayout(dlg)
        vbox.addWidget(QLabel("YOLOモデルを選択してください："))
        model_combo = QComboBox()
        # --- 共通化: ModelManagerでモデル一覧取得 ---
        mm = ModelManager()
        model_paths = []
        for cat in mm.categories():
            for path, info in mm.entries(cat):
                model_combo.addItem(f"[{cat}] {info['name']}", path)
                model_paths.append(path)
        vbox.addWidget(model_combo)
        vbox.addWidget(QLabel("検出ラベル（クラス名）を選択してください："))
        class_combo = QComboBox()
        # クラス名リストをdataset.yamlから取得
        import yaml
        dataset_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '../dataset/dataset.yaml'))
        class_names = []
        if os.path.exists(dataset_yaml):
            with open(dataset_yaml, 'r', encoding='utf-8') as f:
                ydata = yaml.safe_load(f)
            if 'names' in ydata:
                if isinstance(ydata['names'], dict):
                    class_names = [v for k, v in sorted(ydata['names'].items())]
                elif isinstance(ydata['names'], list):
                    class_names = ydata['names']
        for cname in class_names:
            class_combo.addItem(cname)
        vbox.addWidget(class_combo)
        btn = QPushButton("YOLOでbbox補完を実行")
        vbox.addWidget(btn)
        def on_reassign():
            model_path = model_combo.currentData()
            class_name = class_combo.currentText()
            images = all_images
            if not images:
                QMessageBox.warning(dlg, "警告", "再検出対象画像がありません。")
                return
            # 破損画像を除外
            valid_images = []
            corrupt_images = []
            for img in images:
                try:
                    with Image.open(img) as im:
                        im.verify()
                    valid_images.append(img)
                except Exception:
                    corrupt_images.append(img)
            if corrupt_images:
                QMessageBox.warning(dlg, "警告", f"破損画像を除外しました: {len(corrupt_images)}件\n" + '\n'.join(corrupt_images[:10]) + ("\n..." if len(corrupt_images)>10 else ""))
            if not valid_images:
                QMessageBox.critical(dlg, "エラー", "有効な画像がありません。")
                return
            # CLIで再検出
            import subprocess, tempfile, sys
            with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.txt') as tf:
                for img in valid_images:
                    tf.write(img + '\n')
                imglist_path = tf.name
            out_json = imglist_path + '_bbox.json'
            cli_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../utils/yolo_predict_cli.py'))
            cmd = [sys.executable, cli_path,
                   '--input_list', imglist_path, '--output_json', out_json,
                   '--model', model_path, '--class', class_name]
            try:
                subprocess.run(cmd, check=True)
            except Exception as e:
                QMessageBox.critical(dlg, "エラー", f"再検出コマンド失敗: {e}")
                return
            # bbox_dictを読み込み
            try:
                with open(out_json, 'r', encoding='utf-8') as f:
                    bbox_dict = json.load(f)
            except Exception as e:
                QMessageBox.critical(dlg, "エラー", f"bbox結果の読込失敗: {e}")
                return
            # 上書き保存（既存ロール割当は維持し、bboxのみ補完）
            for role_label, img_list in no_bbox_dict.items():
                self.set_images(img_list, bbox_dict)
                self.save_to_json(role_label, img_list)
            QMessageBox.information(dlg, "完了", "YOLOラベル再検出によるbbox補完が完了しました。")
            dlg.accept()
        btn.clicked.connect(on_reassign)
        dlg.exec()

    def export_yolo_from_roles(self):
        # seedsディレクトリ内の全ロールJSONを対象
        json_dir = self.save_dir
        json_paths = [str(Path(json_dir)/f) for f in os.listdir(json_dir) if f.endswith('.json')]
        if not json_paths:
            QMessageBox.warning(self, "エラー", "ロール割当JSONが見つかりません")
            return
        
        try:
            # データセット変換前の確認ダイアログ
            dlg = QDialog(self)
            dlg.setWindowTitle("YOLOエクスポートオプション")
            layout = QVBoxLayout(dlg)
            
            # 説明テキスト
            layout.addWidget(QLabel("エクスポートオプションを設定してください:"))
            
            # オプション1: ネットワークドライブの画像をローカルにコピー
            copy_network_cb = QCheckBox("ネットワークドライブの画像をテンポラリにコピー (H:/ などのパス)")
            copy_network_cb.setChecked(True)
            layout.addWidget(copy_network_cb)
            
            # オプション2: 画像が存在しないパスをスキップ
            skip_missing_cb = QCheckBox("存在しない画像パスをスキップ")
            skip_missing_cb.setChecked(True)
            layout.addWidget(skip_missing_cb)
            
            # 設定確定ボタン
            btn = QPushButton("エクスポート開始")
            layout.addWidget(btn)
            
            # 戻り値用の変数
            options = {"copy_network": True, "skip_missing": True}
            
            # ボタンクリック時の処理
            def on_btn_clicked():
                options["copy_network"] = copy_network_cb.isChecked()
                options["skip_missing"] = skip_missing_cb.isChecked()
                dlg.accept()
            
            btn.clicked.connect(on_btn_clicked)
            
            # ダイアログ表示
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            
            # データセット変換
            dataset = convert_role_json_to_annotation_dataset(
                json_paths, 
                copy_network_drive=options["copy_network"],
                skip_missing_files=options["skip_missing"]
            )
            
            # 変換結果の確認
            if not dataset.classes:
                QMessageBox.warning(self, "エラー", "クラス定義が作成できませんでした。JSONファイルの形式を確認してください。")
                return
                
            if not dataset.annotations:
                QMessageBox.warning(self, "エラー", "アノテーションが作成できませんでした。JSONファイルの内容を確認してください。")
                return
            
            # 詳細ログ出力
            print(f"読み込んだJSON: {len(json_paths)}件")
            print(f"クラス数: {len(dataset.classes)}件")
            print(f"画像数: {len(dataset.annotations)}件")
            
            # デバッグ: 変換に失敗した可能性のある画像パスを検出
            input_images = set()
            for json_path in json_paths:
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for img in data.get('images', []):
                        if isinstance(img, str):
                            input_images.add(img)
                        elif isinstance(img, dict) and 'path' in img:
                            input_images.add(img['path'])
                except Exception as e:
                    print(f"JSONファイル読み込みエラー: {json_path} - {e}")
            
            print(f"元の画像数: {len(input_images)}件")
            print(f"変換後の画像数: {len(dataset.annotations)}件")
            print(f"変換中に失われた画像数: {len(input_images) - len(dataset.annotations)}件")
            
            # 出力先ディレクトリ選択
            export_dir = QFileDialog.getExistingDirectory(self, "YOLOエクスポート先ディレクトリを選択")
            if not export_dir:
                return
            
            # タイムスタンプディレクトリ作成
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = os.path.join(export_dir, f"yolo_export_{timestamp}")
            os.makedirs(export_dir, exist_ok=True)
            
            # デバッグログファイル
            log_file = os.path.join(export_dir, "export_debug.log")
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"元の画像数: {len(input_images)}件\n")
                f.write(f"変換後の画像数: {len(dataset.annotations)}件\n")
                if options["copy_network"]:
                    f.write("オプション: ネットワークドライブの画像をテンポラリにコピー\n")
                if options["skip_missing"]:
                    f.write("オプション: 存在しない画像パスをスキップ\n")
                f.write("変換できなかった画像パス:\n")
                for img in input_images:
                    if img not in dataset.annotations:
                        f.write(f"{img}\n")
            
            # エクスポート処理
            # --- 旧: result = export_to_yolo(dataset, export_dir) ---
            # 新: YoloDatasetExporterでエクスポート
            from src.yolo_dataset_exporter import YoloDatasetExporter
            # dataset.images, dataset.annotations, dataset.classes などを使ってエクスポーターを初期化
            # 必要に応じて一時的なJSONを作成
            import json
            image_list_json = os.path.join(export_dir, 'image_list.json')
            image_list = []
            for img_path in dataset.images:
                bboxes = dataset.annotations.get(img_path, [])
                image_list.append({'filename': os.path.basename(img_path), 'image_path': img_path, 'bboxes': bboxes})
            with open(image_list_json, 'w', encoding='utf-8') as f:
                json.dump(image_list, f, ensure_ascii=False, indent=2)
            exporter = YoloDatasetExporter([image_list_json], output_dir=export_dir, val_ratio=0.0)
            exporter.export(force_flush=True)
            result = {
                'export_path': export_dir,
                'classes': len(exporter.classes),
                'images': len(exporter.images),
                'images_success': len(exporter.images),
                'images_failed': 0,
                'annotations': sum(len(v) for v in exporter.annotations.values()),
                'failed_paths_file': None
            }
            
            # 結果メッセージの作成
            result_msg = f"YOLOデータセットをエクスポートしました:\n\n" \
                        f"出力先: {result['export_path']}\n" \
                        f"クラス数: {result['classes']}\n" \
                        f"処理画像数: {result['images']}\n" \
                        f"成功: {result.get('images_success', 0)}件\n" \
                        f"失敗: {result.get('images_failed', 0)}件\n" \
                        f"アノテーション数: {result['annotations']}\n" \
                        f"変換前の元画像: {len(input_images)}件\n" \
                        f"デバッグログ: {log_file}\n"
            
            # 失敗ファイルがある場合は追加情報
            if result.get('failed_paths_file') and os.path.exists(result['failed_paths_file']):
                result_msg += f"\n失敗ファイルリスト: {result['failed_paths_file']}"
            
            QMessageBox.information(self, "完了", result_msg)
            
        except Exception as e:
            import traceback
            error_msg = f"エクスポート中にエラーが発生しました: {str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "エラー", error_msg)

    def validate_image_paths(self):
        """
        割り当てられた画像パスの存在を検証するデバッグ機能
        """
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QProgressBar
        import threading
        
        # 検証用ダイアログ作成
        dlg = QDialog(self)
        dlg.setWindowTitle("画像パス検証")
        dlg.resize(800, 600)
        layout = QVBoxLayout(dlg)
        
        # 進捗表示
        progress_label = QLabel("検証準備中...")
        layout.addWidget(progress_label)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        layout.addWidget(progress_bar)
        
        # 結果表示エリア
        result_edit = QTextEdit()
        result_edit.setReadOnly(True)
        layout.addWidget(result_edit)
        
        # ボタン
        btn_close = QPushButton("閉じる")
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        
        dlg.show()  # 先に表示
        
        # ログ出力関数
        def log(msg):
            result_edit.append(msg)
            # スクロールを最下部に
            cursor = result_edit.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            result_edit.setTextCursor(cursor)
        
        # 検証実行関数
        def validate():
            seed_dir = self.save_dir
            json_files = [os.path.join(seed_dir, f) for f in os.listdir(seed_dir) if f.endswith('.json')]
            
            if not json_files:
                log("JSONファイルが見つかりません。")
                progress_label.setText("検証完了")
                return
                
            log(f"JSONファイル数: {len(json_files)}件")
            
            # 統計情報
            total_images = 0
            existing_images = 0
            missing_images = 0
            
            # 存在しないファイルリスト
            missing_files = []
            
            # 各JSONファイルを処理
            for i, json_path in enumerate(json_files):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    label = data.get('label', os.path.basename(json_path).replace('.json', ''))
                    log(f"\n検証中: {label}")
                    
                    # 画像リスト取得
                    images = data.get('images', [])
                    file_count = len(images)
                    log(f"  登録画像数: {file_count}件")
                    
                    # 進捗更新
                    file_existing = 0
                    file_missing = 0;
                    
                    for j, img in enumerate(images):
                        # 進捗表示更新
                        progress = int((i * 100 / len(json_files)) + (j * 100 / (file_count * len(json_files))))
                        progress_bar.setValue(min(progress, 100))
                        progress_label.setText(f"検証中: {label} ({j+1}/{file_count})")
                        
                        # パス取得
                        if isinstance(img, str):
                            img_path = img
                        else:
                            img_path = img.get('path', '')
                        
                        total_images += 1
                        
                        # 存在確認
                        if os.path.exists(img_path):
                            file_existing += 1
                            existing_images += 1
                        else:
                            # バックスラッシュ/フォワードスラッシュ変換して再試行
                            alt_path = img_path.replace('\\', '/')
                            if os.path.exists(alt_path):
                                file_existing += 1
                                existing_images += 1
                                log(f"  警告: パス形式の問題 - {img_path}")
                            else:
                                alt_path = img_path.replace('/', '\\')
                                if os.path.exists(alt_path):
                                    file_existing += 1
                                    existing_images += 1
                                    log(f"  警告: パス形式の問題 - {img_path}")
                                else:
                                    file_missing += 1
                                    missing_images += 1
                                    missing_files.append(img_path)
                                    log(f"  エラー: ファイルなし - {img_path}")
                    
                    log(f"  結果: 存在={file_existing}件, 欠損={file_missing}件")
                    
                except Exception as e:
                    log(f"JSONファイル処理エラー: {json_path} - {e}")
            
            # 最終結果
            log("\n\n検証完了")
            log(f"総画像数: {total_images}件")
            log(f"存在する画像: {existing_images}件")
            log(f"欠損画像: {missing_images}件")
            
            # 欠損ファイルの詳細リスト
            if missing_files:
                log("\n欠損ファイル一覧:")
                for path in missing_files:
                    log(path)
            
            progress_label.setText("検証完了")
            progress_bar.setValue(100)
        
        # 別スレッドで検証実行
        threading.Thread(target=validate, daemon=True).start()
        
        # ダイアログ表示
        dlg.exec()

    def closeEvent(self, event):
        self.save_window_settings()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        from PyQt6.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        
        # コンテキストメニューのアクション追加
        action_export = QAction("YOLOエクスポート", self)
        action_export.triggered.connect(self.export_yolo_from_roles)
        menu.addAction(action_export)
        
        action_reassign = QAction("bboxなし画像の再検出", self)
        action_reassign.triggered.connect(self.show_reassign_dialog)
        menu.addAction(action_reassign)
        
        # バウンディングボックス補完機能を追加
        action_bbox_completion = QAction("バウンディングボックス自動補完", self)
        action_bbox_completion.triggered.connect(self.show_bbox_completion_dialog)
        menu.addAction(action_bbox_completion)
        
        # デバッグツール追加
        menu.addSeparator()
        action_validate = QAction("画像パス検証", self)
        action_validate.triggered.connect(self.validate_image_paths)
        menu.addAction(action_validate)
        
        menu.exec(event.globalPos())

    def show_bbox_completion_dialog(self):
        """
        バウンディングボックス自動補完ダイアログを表示
        YOLOモデルを使って画像内の人物を検出し、バウンディングボックスを自動補完します
        """
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                    QPushButton, QComboBox, QProgressBar, QTextEdit, 
                                    QDialogButtonBox, QCheckBox, QGroupBox, QSpinBox)
        from PyQt6.QtCore import Qt, QThread, QTimer
        import glob
        
        # BBoxCompletionWorkerクラスをインポート
        from src.utils.bbox_completion_worker import BBoxCompletionWorker
        
        # JSONファイルのパスリスト
        json_dir = self.save_dir
        json_paths = [os.path.join(json_dir, f) for f in os.listdir(json_dir) if f.endswith('.json')]
        if not json_paths:
            QMessageBox.warning(self, "エラー", "ロール割当JSONが見つかりません")
            return
        
        # ダイアログ作成
        dlg = QDialog(self)
        dlg.setWindowTitle("バウンディングボックス自動補完")
        dlg.resize(900, 700)
        layout = QVBoxLayout(dlg)
        
        # 設定グループ
        settings_group = QGroupBox("検出設定")
        settings_layout = QVBoxLayout(settings_group)
        
        # モデル選択
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("YOLOモデル:"))
        model_combo = QComboBox()
        
        # モデル一覧を取得
        mm = ModelManager()
        model_paths = []
        
        # デフォルトモデル
        model_combo.addItem("YOLOv8n (標準)", "yolov8n.pt")
        model_paths.append("yolov8n.pt")
        
        for cat in mm.categories():
            for path, info in mm.entries(cat):
                if path.endswith('.pt'):  # YOLOモデルのみを表示
                    model_combo.addItem(f"[{cat}] {info['name']}", path)
                    model_paths.append(path)
        
        model_layout.addWidget(model_combo, 1)
        settings_layout.addLayout(model_layout)
        
        # クラス選択
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel("検出クラス:"))
        class_combo = QComboBox()
        
        # よく使うクラス名を追加
        common_classes = ["person", "worker", "people", "human"]
        for cls in common_classes:
            class_combo.addItem(cls)
        
        # dataset.yamlからクラス名を取得
        import yaml
        dataset_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), '../dataset/dataset.yaml'))
        if os.path.exists(dataset_yaml):
            try:
                with open(dataset_yaml, 'r', encoding='utf-8') as f:
                    ydata = yaml.safe_load(f)
                if 'names' in ydata:
                    if isinstance(ydata['names'], dict):
                        class_names = [v for k, v in sorted(ydata['names'].items())]
                    elif isinstance(ydata['names'], list):
                        class_names = ydata['names']
                    
                    # 重複を避けて追加
                    for cname in class_names:
                        if cname not in common_classes:
                            class_combo.addItem(cname)
            except Exception as e:
                print(f"dataset.yaml読み込みエラー: {e}")
        
        class_layout.addWidget(class_combo, 1)
        settings_layout.addLayout(class_layout)
        
        # 信頼度閾値
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("検出信頼度閾値:"))
        conf_spin = QSpinBox()
        conf_spin.setRange(1, 99)
        conf_spin.setValue(25)
        conf_spin.setSuffix(" %")
        conf_layout.addWidget(conf_spin)
        conf_layout.addStretch(1)
        settings_layout.addLayout(conf_layout)
        
        layout.addWidget(settings_group)
        
        # 進捗表示エリア
        progress_group = QGroupBox("処理状況")
        progress_layout = QVBoxLayout(progress_group)
        
        # ステータスラベル
        status_label = QLabel("準備完了")
        progress_layout.addWidget(status_label)
        
        # 進捗バー
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_layout.addWidget(progress_bar)
        
        # 詳細ログエリア
        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        log_edit.setMaximumHeight(250)
        progress_layout.addWidget(log_edit)
        
        layout.addWidget(progress_group)
        
        # ボタン
        button_box = QDialogButtonBox()
        start_button = QPushButton("補完開始")
        start_button.clicked.connect(lambda: start_process())
        button_box.addButton(start_button, QDialogButtonBox.ButtonRole.ActionRole)
        
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(dlg.accept)
        button_box.addButton(close_button, QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(button_box)
        
        # ログ出力関数
        def add_log(message):
            log_edit.append(message)
            # 自動スクロール
            log_edit.verticalScrollBar().setValue(log_edit.verticalScrollBar().maximum())
        
        # ステータス更新関数
        def update_status(message):
            status_label.setText(message)
            add_log(message)
        
        # エラー表示関数
        def show_error(message):
            QMessageBox.critical(dlg, "エラー", message)
            add_log(f"エラー: {message}")
        
        # 進捗更新関数
        def update_progress(current, total, message=None):
            progress = int(current / total * 100) if total > 0 else 0
            progress_bar.setValue(progress)
            if message:
                add_log(message)
        
        # 処理完了関数
        def process_completed(results):
            update_status("処理完了")
            progress_bar.setValue(100)
            
            # 結果サマリー
            summary = f"""
            バウンディングボックス補完結果:
            ------------------------------
            処理対象画像数: {results['total_images']}件
            有効画像数: {results['valid_images']}件
            無効画像数: {results['invalid_images']}件
            検出成功画像数: {results['detected_images']}件
            更新された画像数: {results['updated_images']}件
            一時ディレクトリ: {results['temp_dir']}
            検出結果バックアップ: {results['backup_json']}
            """
            add_log(summary)
            
            # ロールごとの更新数
            add_log("ロールごとの更新数:")
            for role, count in results['updated_files'].items():
                add_log(f"- {role}: {count}件")
            
            # 完了メッセージ
            if results['updated_images'] > 0:
                QMessageBox.information(
                    dlg, 
                    "補完完了", 
                    f"バウンディングボックス補完が完了しました。\n\n"
                    f"更新された画像数: {results['updated_images']}件"
                )
                # 親ウィジェットのエントリー数を更新
                self.role_list.update_entry_counts()
            else:
                QMessageBox.information(
                    dlg, 
                    "補完完了", 
                    "更新された画像はありませんでした。"
                )
            
            # ボタンを有効化
            start_button.setEnabled(True)
        
        # 処理開始関数
        def start_process():
            # 入力値を取得
            model_path = model_combo.currentData()
            class_name = class_combo.currentText()
            confidence = conf_spin.value() / 100.0
            
            # UIをクリア
            log_edit.clear()
            progress_bar.setValue(0)
            update_status("処理を開始しています...")
            
            # ボタンを無効化
            start_button.setEnabled(False)
            
            # ワーカーを作成
            worker = BBoxCompletionWorker(json_paths, model_path, class_name, confidence)
            
            # シグナル接続
            worker.status_updated.connect(update_status)
            worker.progress_updated.connect(update_progress)
            worker.error_occurred.connect(show_error)
            worker.process_completed.connect(process_completed)
            
            # バックグラウンド処理開始
            worker.start()
            
            # 参照を保持しておく（ガベージコレクション対策）
            dlg.worker = worker
        
        # ダイアログ表示
        dlg.exec()

if __name__ == "__main__":
    import sys
    import json
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    widget = DetectResultWidget()
    # 起動直後に画像ディレクトリ選択ダイアログを出さない
    widget.set_images([])
    widget.show()
    # アプリ終了時に画像リストとウィンドウ設定を保存
    def save_all():
        model = widget.image_widget.fast_thumb_list.model_ref
        if model is not None:
            with open("last_images.json", "w", encoding="utf-8") as f:
                json.dump(model.image_paths, f, ensure_ascii=False, indent=2)
        widget.save_window_settings()
    app.aboutToQuit.connect(save_all)
    sys.exit(app.exec())