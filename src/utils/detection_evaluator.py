#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
検出結果の可視化と定量評価を行うユーティリティ
"""
import os
import json
import time
import logging
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional, Any
from tqdm import tqdm

# 自前の関数をインポート
from src.utils.auto_annotate import detect_objects_in_image, _init_grounding_dino_sam

# ロガー設定
logger = logging.getLogger(__name__)


class DetectionEvaluator:
    """検出結果の可視化と評価を行うクラス"""
    
    def __init__(
        self,
        json_path: Union[str, Path],
        output_dir: Union[str, Path] = None,
        class_names: List[str] = None,
        iou_threshold: float = 0.5,
        confidence_threshold: float = 0.3,
        use_gpu: bool = False
    ):
        """初期化
        
        Args:
            json_path: アノテーションJSONファイルのパス
            output_dir: 出力ディレクトリ
            class_names: 評価対象のクラス名リスト (Noneの場合はすべてのクラスを評価)
            iou_threshold: IoUの閾値（この値以上でTrue Positiveと判定）
            confidence_threshold: 検出信頼度の閾値
            use_gpu: GPUを使用するかどうか
        """
        self.json_path = Path(json_path)
        if output_dir is None:
            self.output_dir = Path("detection_results")
        else:
            self.output_dir = Path(output_dir)
        
        # 出力ディレクトリを作成
        (self.output_dir / "visualizations").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "metrics").mkdir(parents=True, exist_ok=True)
        
        # 設定
        self.class_names = class_names
        self.iou_threshold = iou_threshold
        self.confidence_threshold = confidence_threshold
        self.use_gpu = use_gpu
        
        # 結果保存用
        self.results = {}
        self.metrics = {}
        
        # JSONデータ読み込み
        self._load_json()
        
        # モデル初期化
        logger.info("GroundingDINO + SAMモデルを初期化しています...")
        self.detector = _init_grounding_dino_sam(use_gpu=self.use_gpu)
        logger.info("モデル初期化完了")
    
    def _load_json(self):
        """アノテーションJSONファイルを読み込む"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # base_pathの確認と設定
        self.base_path = Path(self.data.get('base_path', ''))
        if not self.base_path.exists():
            logger.warning(f"base_path {self.base_path} が存在しません。相対パスを使用します。")
            self.base_path = self.json_path.parent
        
        # クラスIDとクラス名のマッピングを作成
        self.class_mapping = {cls['id']: cls['name'] for cls in self.data['classes']}
        self.class_ids = {cls['name']: cls['id'] for cls in self.data['classes']}
        
        # 評価対象のクラスを設定
        if self.class_names is None:
            self.class_names = list(self.class_ids.keys())
        
        logger.info(f"JSONデータ読み込み完了: {len(self.data['annotations'])}枚の画像, {len(self.class_names)}クラス")
    
    def evaluate_all(self) -> Dict[str, Any]:
        """すべての画像に対して評価を実行"""
        logger.info(f"評価開始: {len(self.data['annotations'])}枚の画像, {self.class_names}クラス")
        
        # 評価結果保存用
        self.results = {cls_name: {
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'iou_values': []
        } for cls_name in self.class_names}
        
        # 各画像に対して評価
        start_time = time.time()
        for i, (img_path, annotations) in enumerate(tqdm(self.data['annotations'].items(), desc="画像評価中")):
            logger.info(f"画像 {i+1}/{len(self.data['annotations'])}: {img_path}")
            self.evaluate_image(img_path, annotations)
        
        # 評価時間
        eval_time = time.time() - start_time
        
        # メトリクスを計算
        self._calculate_metrics()
        
        # 結果をCSVに保存
        self._save_results()
        
        logger.info(f"評価完了: 所要時間={eval_time:.2f}秒")
        return self.metrics
    
    def evaluate_image(self, img_path: str, annotations: List[Dict]) -> Dict[str, Any]:
        """1枚の画像に対して評価を実行
        
        Args:
            img_path: 画像の相対パス
            annotations: アノテーションデータ
        
        Returns:
            評価結果
        """
        # 画像パスを解決
        full_img_path = self.base_path / img_path
        if not full_img_path.exists():
            logger.warning(f"画像ファイル {full_img_path} が見つかりません。スキップします。")
            return {}
        
        # GroundTruthボックスを準備
        gt_boxes = {cls_name: [] for cls_name in self.class_names}
        for ann in annotations:
            cls_id = ann.get('class_id')
            cls_name = self.class_mapping.get(cls_id, 'unknown')
            if cls_name in self.class_names:
                box = ann.get('box', [])
                if len(box) == 4:
                    gt_boxes[cls_name].append(box)
        
        # 画像を読み込み
        try:
            image = cv2.imread(str(full_img_path))
            if image is None:
                logger.error(f"画像 {full_img_path} を読み込めませんでした。スキップします。")
                return {}
            image_h, image_w = image.shape[:2]
        except Exception as e:
            logger.error(f"画像 {full_img_path} の読み込み中にエラーが発生しました: {e}")
            return {}
        
        # 可視化用の画像をコピー
        vis_image = image.copy()
        
        # 各クラスに対して検出実行
        all_detections = {}
        for cls_name in self.class_names:
            # 検出実行
            detections = self._detect_objects(str(full_img_path), cls_name)
            
            # 閾値でフィルタリング
            filtered_detections = [
                det for det in detections 
                if det.get('score', 0) >= self.confidence_threshold
            ]
            
            all_detections[cls_name] = filtered_detections
            
            # 検出結果を可視化
            for det in filtered_detections:
                box = det.get('bbox', [])
                if len(box) == 4:
                    x1, y1, x2, y2 = map(int, box)
                    color = self._get_color_for_class(cls_name)
                    cv2.rectangle(vis_image, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        vis_image, 
                        f"{cls_name} {det.get('score', 0):.2f}", 
                        (x1, y1 - 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, 
                        color, 
                        2
                    )
            
            # GroundTruthボックスを可視化（点線）
            for box in gt_boxes[cls_name]:
                x1, y1, x2, y2 = map(int, box)
                color = self._get_color_for_class(cls_name, is_gt=True)
                # LINE_DASHEDが利用できない場合は通常の線を使用
                # 点線効果を出すためにいくつかの短い線分を描画
                line_length = 5
                gap_length = 3
                
                # 上側の線
                for x in range(x1, x2, line_length + gap_length):
                    x_end = min(x + line_length, x2)
                    cv2.line(vis_image, (x, y1), (x_end, y1), color, 1)
                
                # 右側の線
                for y in range(y1, y2, line_length + gap_length):
                    y_end = min(y + line_length, y2)
                    cv2.line(vis_image, (x2, y), (x2, y_end), color, 1)
                
                # 下側の線
                for x in range(x2, x1, -(line_length + gap_length)):
                    x_end = max(x - line_length, x1)
                    cv2.line(vis_image, (x, y2), (x_end, y2), color, 1)
                
                # 左側の線
                for y in range(y2, y1, -(line_length + gap_length)):
                    y_end = max(y - line_length, y1)
                    cv2.line(vis_image, (x1, y), (x1, y_end), color, 1)
            
            # 評価: クラスごとにTP, FP, FNを計算
            self._evaluate_detections(cls_name, filtered_detections, gt_boxes[cls_name])
        
        # 可視化画像を保存
        output_img_path = self.output_dir / "visualizations" / f"{Path(img_path).stem}_result.jpg"
        cv2.imwrite(str(output_img_path), vis_image)
        
        return all_detections
    
    def _detect_objects(self, img_path: str, cls_name: str) -> List[Dict]:
        """オブジェクト検出を実行
        
        Args:
            img_path: 画像パス
            cls_name: 検出対象のクラス名
        
        Returns:
            検出結果リスト
        """
        try:
            text_prompt = f"{cls_name} ."
            results = detect_objects_in_image(img_path, text_prompt)
            return results
        except Exception as e:
            logger.error(f"検出中にエラーが発生しました: {e}")
            return []
    
    def _evaluate_detections(
        self, 
        cls_name: str, 
        detections: List[Dict], 
        gt_boxes: List[List[float]]
    ):
        """検出結果を評価
        
        Args:
            cls_name: クラス名
            detections: 検出結果
            gt_boxes: GroundTruthボックス
        """
        # 検出結果とGTのペアとIoUを記録
        matches = []
        
        # 検出ボックスをリストに変換
        det_boxes = []
        for det in detections:
            box = det.get('bbox', [])
            if len(box) == 4:
                det_boxes.append(box)
        
        # マッチングマトリックスを作成 (IoU値)
        if len(det_boxes) > 0 and len(gt_boxes) > 0:
            iou_matrix = self._calculate_iou_matrix(det_boxes, gt_boxes)
            
            # マッチングを行う
            # これは簡易的な実装で、各GTに最高のIoUを持つ検出をマッチ
            # より高度なマッチングアルゴリズム（ハンガリアン法など）も検討可
            matched_gt = set()
            for det_idx, det_box in enumerate(det_boxes):
                best_iou = -1
                best_gt_idx = -1
                
                for gt_idx, gt_box in enumerate(gt_boxes):
                    if gt_idx in matched_gt:
                        continue  # 既にマッチしたGTはスキップ
                    
                    iou = iou_matrix[det_idx, gt_idx]
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = gt_idx
                
                if best_iou >= self.iou_threshold and best_gt_idx not in matched_gt:
                    matches.append((det_idx, best_gt_idx, best_iou))
                    matched_gt.add(best_gt_idx)
                    self.results[cls_name]['true_positives'] += 1
                    self.results[cls_name]['iou_values'].append(best_iou)
                else:
                    self.results[cls_name]['false_positives'] += 1
            
            # マッチしなかったGTはFalse Negative
            self.results[cls_name]['false_negatives'] += len(gt_boxes) - len(matched_gt)
        else:
            # 検出結果がない場合はすべてFalse Negative
            if len(gt_boxes) > 0:
                self.results[cls_name]['false_negatives'] += len(gt_boxes)
            
            # GTがない場合はすべてFalse Positive
            if len(det_boxes) > 0:
                self.results[cls_name]['false_positives'] += len(det_boxes)
    
    def _calculate_iou_matrix(
        self, 
        boxes_a: List[List[float]], 
        boxes_b: List[List[float]]
    ) -> np.ndarray:
        """2つのボックスセット間のIoUマトリックスを計算
        
        Args:
            boxes_a: ボックスセットA [x1, y1, x2, y2]
            boxes_b: ボックスセットB [x1, y1, x2, y2]
        
        Returns:
            IoUマトリックス (shape=[len(boxes_a), len(boxes_b)])
        """
        num_a = len(boxes_a)
        num_b = len(boxes_b)
        iou_matrix = np.zeros((num_a, num_b))
        
        for i, box_a in enumerate(boxes_a):
            for j, box_b in enumerate(boxes_b):
                iou_matrix[i, j] = self._calculate_iou(box_a, box_b)
        
        return iou_matrix
    
    def _calculate_iou(self, box_a: List[float], box_b: List[float]) -> float:
        """2つのボックス間のIoUを計算
        
        Args:
            box_a: ボックスA [x1, y1, x2, y2]
            box_b: ボックスB [x1, y1, x2, y2]
            
        Returns:
            IoU値
        """
        # Convert boxes to numpy arrays
        box_a = np.array(box_a)
        box_b = np.array(box_b)
        
        # Calculate intersection area
        x1 = max(box_a[0], box_b[0])
        y1 = max(box_a[1], box_b[1])
        x2 = min(box_a[2], box_b[2])
        y2 = min(box_a[3], box_b[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection_area = (x2 - x1) * (y2 - y1)
        
        # Calculate union area
        box_a_area = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        box_b_area = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union_area = box_a_area + box_b_area - intersection_area
        
        # Calculate IoU
        if union_area <= 0:
            return 0.0
        
        return intersection_area / union_area
    
    def _calculate_metrics(self):
        """評価指標を計算"""
        self.metrics = {'per_class': {}, 'overall': {}}
        
        total_tp = 0
        total_fp = 0
        total_fn = 0
        
        for cls_name in self.class_names:
            cls_result = self.results[cls_name]
            tp = cls_result['true_positives']
            fp = cls_result['false_positives']
            fn = cls_result['false_negatives']
            
            total_tp += tp
            total_fp += fp
            total_fn += fn
            
            # クラスごとの指標
            precision = tp / (tp + fp) if tp + fp > 0 else 0
            recall = tp / (tp + fn) if tp + fn > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
            mean_iou = np.mean(cls_result['iou_values']) if cls_result['iou_values'] else 0
            
            self.metrics['per_class'][cls_name] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'mean_iou': mean_iou,
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn
            }
        
        # 全体の指標
        precision = total_tp / (total_tp + total_fp) if total_tp + total_fp > 0 else 0
        recall = total_tp / (total_tp + total_fn) if total_tp + total_fn > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
        
        # 全クラスのIoU値を集めて平均を計算
        all_ious = []
        for cls_name in self.class_names:
            all_ious.extend(self.results[cls_name]['iou_values'])
        
        overall_mean_iou = np.mean(all_ious) if all_ious else 0
        
        self.metrics['overall'] = {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'mean_iou': overall_mean_iou,
            'true_positives': total_tp,
            'false_positives': total_fp,
            'false_negatives': total_fn
        }
    
    def _save_results(self):
        """評価結果をCSVに保存"""
        # クラスごとの結果
        per_class_df = []
        for cls_name, metrics in self.metrics['per_class'].items():
            row = {'class': cls_name}
            row.update(metrics)
            per_class_df.append(row)
        
        per_class_df = pd.DataFrame(per_class_df)
        per_class_df.to_csv(self.output_dir / "metrics" / "per_class_metrics.csv", index=False)
        
        # 全体の結果
        overall_df = pd.DataFrame([self.metrics['overall']])
        overall_df.to_csv(self.output_dir / "metrics" / "overall_metrics.csv", index=False)
        
        # 結果をテキストファイルにも保存
        with open(self.output_dir / "metrics" / "evaluation_report.txt", 'w', encoding='utf-8') as f:
            f.write("=== 検出評価レポート ===\n\n")
            f.write(f"評価日時: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"JSONパス: {self.json_path}\n")
            f.write(f"クラス: {', '.join(self.class_names)}\n")
            f.write(f"IoU閾値: {self.iou_threshold}\n")
            f.write(f"信頼度閾値: {self.confidence_threshold}\n\n")
            
            f.write("--- クラスごとの結果 ---\n")
            for cls_name, metrics in self.metrics['per_class'].items():
                f.write(f"\n{cls_name}:\n")
                f.write(f"  Precision: {metrics['precision']:.4f}\n")
                f.write(f"  Recall: {metrics['recall']:.4f}\n")
                f.write(f"  F1 Score: {metrics['f1_score']:.4f}\n")
                f.write(f"  Mean IoU: {metrics['mean_iou']:.4f}\n")
                f.write(f"  TP: {metrics['true_positives']}, FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}\n")
            
            f.write("\n--- 全体の結果 ---\n")
            f.write(f"Precision: {self.metrics['overall']['precision']:.4f}\n")
            f.write(f"Recall: {self.metrics['overall']['recall']:.4f}\n")
            f.write(f"F1 Score: {self.metrics['overall']['f1_score']:.4f}\n")
            f.write(f"TP: {self.metrics['overall']['true_positives']}, FP: {self.metrics['overall']['false_positives']}, FN: {self.metrics['overall']['false_negatives']}\n")
    
    def _get_color_for_class(self, cls_name: str, is_gt: bool = False) -> Tuple[int, int, int]:
        """クラス名に基づいて色を決定
        
        Args:
            cls_name: クラス名
            is_gt: GroundTruthかどうか
        
        Returns:
            BGR色
        """
        # クラス名をハッシュ化して色を決定
        import hashlib
        hash_obj = hashlib.md5(cls_name.encode())
        hash_val = int(hash_obj.hexdigest(), 16)
        
        r = (hash_val & 0xFF0000) >> 16
        g = (hash_val & 0x00FF00) >> 8
        b = hash_val & 0x0000FF
        
        # GTの場合は薄い色に
        if is_gt:
            r = min(255, r + 100)
            g = min(255, g + 100)
            b = min(255, b + 100)
        
        return (b, g, r)  # OpenCVはBGR形式 