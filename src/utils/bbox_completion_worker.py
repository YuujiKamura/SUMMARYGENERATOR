#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
バウンディングボックス補完のワーカークラス
スレッド処理でUIをブロックしないようにします
"""

import os
import sys
import json
import shutil
import tempfile
import hashlib
import traceback
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

class BBoxCompletionWorker(QThread):
    """バウンディングボックス補完を行うスレッドワーカー"""
    
    # 進捗報告用シグナル
    progress_updated = pyqtSignal(int, int, str)  # (current, total, message)
    status_updated = pyqtSignal(str)  # ステータスメッセージ
    error_occurred = pyqtSignal(str)  # エラーメッセージ
    process_completed = pyqtSignal(dict)  # 処理結果
    
    def __init__(self, json_paths, model_path="yolov8n.pt", class_name="person", confidence=0.25):
        """
        バウンディングボックス補完ワーカーの初期化
        
        Args:
            json_paths: 処理対象のJSONファイルパスリスト
            model_path: 使用するYOLOモデルのパス
            class_name: 検出対象のクラス名
            confidence: 検出信頼度の閾値
        """
        super().__init__()
        self.json_paths = json_paths
        self.model_path = model_path
        self.class_name = class_name
        self.confidence = confidence
        self.seed_dir = os.path.dirname(json_paths[0]) if json_paths else "seeds"
        self.temp_dir = os.path.join(tempfile.gettempdir(), f"photocategorizer_bbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 結果格納用
        self.results = {
            "updated_files": {},  # ロールごとの更新件数
            "total_images": 0,    # 処理対象の総画像数
            "valid_images": 0,    # 有効な画像数
            "invalid_images": 0,  # 無効な画像数
            "detected_images": 0, # 検出成功した画像数
            "updated_images": 0,  # 更新した画像数
            "temp_dir": self.temp_dir,  # 一時ディレクトリパス
            "backup_json": "",    # バックアップJSONパス
            "error": None,        # エラー情報
        }
    
    def run(self):
        """スレッドメイン処理"""
        try:
            # 1. バウンディングボックスがない画像を検出
            self.status_updated.emit("バウンディングボックスなし画像の検出中...")
            no_bbox_dict = self.find_images_without_bboxes()
            
            # 画像が見つからない場合は終了
            no_bbox_count = sum(len(paths) for paths in no_bbox_dict.values())
            if no_bbox_count == 0:
                self.status_updated.emit("バウンディングボックスなしの画像がありません。")
                self.process_completed.emit(self.results)
                return
            
            self.results["total_images"] = no_bbox_count
            self.status_updated.emit(f"バウンディングボックスなし画像数: {no_bbox_count}件")
            
            # 2. 全画像パスを収集
            all_no_bbox_images = []
            for img_list in no_bbox_dict.values():
                all_no_bbox_images.extend(img_list)
            
            # 3. 画像パスの検証
            self.status_updated.emit("画像パスの検証中...")
            valid_images, invalid_images = self.validate_images(all_no_bbox_images)
            self.results["valid_images"] = len(valid_images)
            self.results["invalid_images"] = len(invalid_images)
            
            if not valid_images:
                self.error_occurred.emit("有効な画像がありません。")
                self.process_completed.emit(self.results)
                return
            
            # 4. ローカルに画像コピー
            self.status_updated.emit("画像を一時フォルダにコピー中...")
            local_images = self.copy_files_to_local(valid_images)
            
            # 5. YOLOモデルによる検出
            self.status_updated.emit(f"YOLOモデル ({self.model_path}) を使用して検出中...")
            detection_results = self.run_yolo_detection(local_images)
            
            if not detection_results:
                self.error_occurred.emit("検出結果が得られませんでした。")
                self.process_completed.emit(self.results)
                return
            
            self.results["detected_images"] = len(detection_results)
            
            # 6. 検出結果を元のパスに関連付け
            self.status_updated.emit("検出結果をマッピング中...")
            path_mapping = {}
            for i, local_path in enumerate(local_images):
                if i < len(valid_images):
                    path_mapping[local_path] = valid_images[i]
            
            original_detection_results = {}
            for img_path, detections in detection_results.items():
                if img_path in path_mapping:
                    original_detection_results[path_mapping[img_path]] = detections
            
            # 7. JSONファイル更新
            self.status_updated.emit("JSONファイルを更新中...")
            updated_files = self.update_json_with_bboxes(no_bbox_dict, original_detection_results)
            
            self.results["updated_files"] = updated_files
            self.results["updated_images"] = sum(updated_files.values())
            
            # 処理完了
            self.status_updated.emit(f"バウンディングボックス補完完了: {self.results['updated_images']}件の画像を更新")
            self.process_completed.emit(self.results)
            
        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            self.results["error"] = str(e)
            self.error_occurred.emit(error_msg)
            traceback.print_exc()
            self.process_completed.emit(self.results)
    
    def find_images_without_bboxes(self):
        """
        JSONファイルからバウンディングボックスがない画像を抽出
        """
        result = {}
        total = len(self.json_paths)
        
        for i, path in enumerate(self.json_paths):
            try:
                self.progress_updated.emit(i+1, total, f"JSONファイル解析中: {os.path.basename(path)}")
                
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                label = data.get('label', os.path.basename(path).replace('.json', ''))
                images = data.get('images', [])
                no_bbox = []
                
                for entry in images:
                    if isinstance(entry, str):
                        no_bbox.append(entry)
                    elif isinstance(entry, dict):
                        path_info = entry.get('path', '')
                        bboxes = entry.get('bboxes', None)
                        if not bboxes:
                            no_bbox.append(path_info)
                
                if no_bbox:
                    result[label] = no_bbox
                    
            except Exception as e:
                self.status_updated.emit(f"JSONファイル読み込みエラー: {path} - {e}")
        
        return result
    
    def validate_images(self, image_paths):
        """
        画像パスのリストを検証し、有効なパスのみを返す
        """
        from PIL import Image
        valid_images = []
        invalid_images = []
        total = len(image_paths)
        
        for i, img_path in enumerate(image_paths):
            try:
                self.progress_updated.emit(i+1, total, f"画像検証中: {os.path.basename(img_path)}")
                
                # 画像ファイルが存在するか確認
                if not os.path.exists(img_path):
                    self.status_updated.emit(f"画像が存在しません: {img_path}")
                    invalid_images.append(img_path)
                    continue
                    
                # 画像として開けるか確認
                try:
                    with Image.open(img_path) as im:
                        im.verify()
                    valid_images.append(img_path)
                except Exception as e:
                    self.status_updated.emit(f"画像読み込みエラー: {img_path} - {e}")
                    invalid_images.append(img_path)
            except Exception as e:
                self.status_updated.emit(f"パス検証エラー: {img_path} - {e}")
                invalid_images.append(img_path)
        
        return valid_images, invalid_images
    
    def copy_files_to_local(self, image_paths):
        """
        画像をローカルの一時ディレクトリにコピー
        """
        local_paths = []
        total = len(image_paths)
        
        for i, img_path in enumerate(image_paths):
            try:
                self.progress_updated.emit(i+1, total, f"画像コピー中: {os.path.basename(img_path)}")
                
                if not os.path.exists(img_path):
                    local_paths.append(None)
                    continue
                    
                # ファイル名をハッシュ化（衝突を避けるため）
                file_hash = hashlib.md5(img_path.encode()).hexdigest()[:8]
                basename = os.path.basename(img_path)
                temp_path = os.path.join(self.temp_dir, f"{file_hash}_{basename}")
                
                # コピー実行
                shutil.copy2(img_path, temp_path)
                local_paths.append(temp_path)
            except Exception as e:
                self.status_updated.emit(f"ファイルコピーエラー: {img_path} - {e}")
                local_paths.append(None)
        
        return [p for p in local_paths if p]
    
    def run_yolo_detection(self, image_paths):
        """
        YOLOモデルを使って画像のバウンディングボックスを検出
        """
        try:
            # 画像リストを一時ファイルに保存
            imglist_path = os.path.join(self.temp_dir, "image_list.txt")
            with open(imglist_path, 'w', encoding='utf-8') as f:
                for img in image_paths:
                    f.write(img + '\n')
            
            # 出力用JSONパス
            out_json = os.path.join(self.temp_dir, "detection_results.json")
            
            # 検出結果の保存先も作成
            bboxes_json = os.path.join(self.temp_dir, "bboxes_backup.json")
            self.results["backup_json"] = bboxes_json
            
            # YOLO予測CLI実行
            import subprocess
            
            cli_path = os.path.join("src", "utils", "yolo_predict_cli.py")
            if not os.path.exists(cli_path):
                cli_path = os.path.join("utils", "yolo_predict_cli.py")
            
            cmd = [
                sys.executable,
                cli_path,
                '--input_list', imglist_path,
                '--output_json', out_json,
                '--model', self.model_path,
                '--class', self.class_name,
                '--conf', str(self.confidence)
            ]
            
            self.status_updated.emit(f"YOLOモデル実行中...")
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    self.status_updated.emit(line.strip())
            
            # 結果を読み込み
            if os.path.exists(out_json):
                with open(out_json, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                # バックアップとして検出結果をコピー
                shutil.copy2(out_json, bboxes_json)
                self.status_updated.emit(f"検出結果のバックアップを保存: {bboxes_json}")
                
                return results
            else:
                self.error_occurred.emit(f"エラー: 出力JSONファイルが作成されませんでした: {out_json}")
                return {}
        except Exception as e:
            self.error_occurred.emit(f"YOLOモデル実行エラー: {e}")
            traceback.print_exc()
            return {}
    
    def update_json_with_bboxes(self, no_bbox_dict, detection_results):
        """
        検出結果を元のJSONファイルに反映
        """
        updated_files = {}
        roles = list(no_bbox_dict.keys())
        total = len(roles)
        
        for i, role_label in enumerate(roles):
            self.progress_updated.emit(i+1, total, f"JSONファイル更新中: {role_label}")
            
            img_paths = no_bbox_dict[role_label]
            json_path = os.path.join(self.seed_dir, f"{role_label}.json")
            
            if not os.path.exists(json_path):
                self.status_updated.emit(f"Warning: JSONファイルが見つかりません: {json_path}")
                continue
            
            try:
                # 元のJSONをバックアップ
                backup_path = os.path.join(self.temp_dir, f"{role_label}_backup.json")
                shutil.copy2(json_path, backup_path)
                self.status_updated.emit(f"JSONバックアップ作成: {backup_path}")
                
                # 元のJSONを読み込み
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 画像エントリを更新
                updated_count = 0
                images = data.get('images', [])
                for j, entry in enumerate(images):
                    img_path = entry if isinstance(entry, str) else entry.get('path', '')
                    
                    # バウンディングボックスがない場合のみ更新
                    if img_path in img_paths and img_path in detection_results:
                        # 文字列エントリを辞書に変換
                        if isinstance(entry, str):
                            images[j] = {"path": img_path, "bboxes": []}
                        
                        # 検出結果を追加
                        detections = detection_results[img_path]
                        if detections:
                            bbox_list = []
                            for class_id, class_name, conf, xyxy in detections:
                                bbox_list.append({
                                    "class_id": class_id,
                                    "bbox": list(map(float, xyxy)),
                                    "confidence": float(conf)
                                })
                            
                            # エントリを更新
                            images[j]["bboxes"] = bbox_list
                            updated_count += 1
                
                # 更新情報を記録
                updated_files[role_label] = updated_count
                
                # 更新したJSONを保存
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                self.error_occurred.emit(f"JSONファイル更新エラー: {json_path} - {e}")
                traceback.print_exc()
        
        return updated_files 