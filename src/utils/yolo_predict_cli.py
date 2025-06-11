#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YOLOモデルを使った画像予測のCLIスクリプト
画像パスリストからバウンディングボックスを検出してJSONで出力します
"""

import os
import sys
import json
import argparse
from pathlib import Path
import traceback

# カレントディレクトリをsrcの親ディレクトリに設定
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if os.path.basename(parent_dir) == 'src':
    os.chdir(os.path.dirname(parent_dir))
else:
    os.chdir(parent_dir)

# モジュールパスの追加
sys.path.insert(0, os.path.abspath('.'))

# YOLOモデルを使って画像リストからバウンディングボックスを検出する
def detect_boxes_with_yolo(image_paths, model_path, selected_class=None, confidence=0.25):
    """
    YOLOモデルを使って画像リストからバウンディングボックスを検出する
    
    Args:
        image_paths: 画像パスのリスト
        model_path: YOLOモデルのパス
        selected_class: 検出対象のクラス名（Noneの場合は全クラス）
        confidence: 検出信頼度の閾値
        
    Returns:
        画像パスをキー、検出結果のリストを値とする辞書
        {画像パス: [(クラスID, クラス名, 信頼度, [x1, y1, x2, y2]), ...], ...}
    """
    # モデルが存在するか確認
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"モデルファイルが見つかりません: {model_path}")
    
    try:
        # ultralyticsパッケージからYOLOモデルを読み込み
        from ultralytics import YOLO
        
        print(f"モデル読み込み: {model_path}")
        model = YOLO(model_path)
        
        # 結果格納用辞書
        results = {}
        
        # 各画像を処理
        total_images = len(image_paths)
        for idx, img_path in enumerate(image_paths):
            try:
                if not os.path.exists(img_path):
                    print(f"  警告: 画像が存在しません: {img_path}")
                    continue
                
                print(f"処理中 [{idx+1}/{total_images}]: {img_path}")
                
                # YOLO検出実行
                preds = model(img_path, conf=confidence, verbose=False)
                
                # バウンディングボックスリスト
                boxes = []
                
                if preds and len(preds) > 0:
                    result = preds[0]
                    if hasattr(result, 'boxes') and len(result.boxes) > 0:
                        boxes_data = result.boxes
                        
                        for i in range(len(boxes_data)):
                            class_id = int(boxes_data.cls[i].item())
                            confidence_score = float(boxes_data.conf[i].item())
                            class_name = result.names[class_id] if hasattr(result, 'names') else str(class_id)
                            
                            # クラス名のフィルタリング
                            if selected_class and class_name != selected_class and str(class_id) != selected_class:
                                continue
                            
                            # バウンディングボックスの座標を取得
                            xyxy = boxes_data.xyxy[i].cpu().numpy().tolist() if hasattr(boxes_data, 'xyxy') else None
                            
                            # 座標がなければスキップ
                            if not xyxy:
                                continue
                            
                            # 検出結果を追加
                            boxes.append((
                                class_id,
                                class_name,
                                confidence_score,
                                xyxy
                            ))
                
                # 検出結果を格納
                if boxes:
                    results[img_path] = boxes
                    print(f"  検出数: {len(boxes)}件")
                else:
                    print(f"  検出なし")
                
            except Exception as e:
                print(f"  エラー: {img_path} - {e}")
                traceback.print_exc()
        
        return results
        
    except Exception as e:
        print(f"検出処理エラー: {e}")
        traceback.print_exc()
        return {}

def main():
    parser = argparse.ArgumentParser(description='YOLOモデルを使った画像検出CLI')
    parser.add_argument('--input_list', required=True, help='画像パスリストのテキストファイル')
    parser.add_argument('--output_json', required=True, help='検出結果を出力するJSONファイルパス')
    parser.add_argument('--model', required=True, help='YOLOモデルファイルのパス')
    parser.add_argument('--class', dest='class_name', help='検出対象のクラス名')
    parser.add_argument('--conf', type=float, default=0.25, help='検出信頼度の閾値 (0.0-1.0)')
    
    args = parser.parse_args()
    
    # 入力ファイルリスト読み込み
    try:
        with open(args.input_list, 'r', encoding='utf-8') as f:
            image_paths = [line.strip() for line in f.readlines() if line.strip()]
        
        if not image_paths:
            print(f"エラー: 有効な画像パスがありません: {args.input_list}")
            return 1
        
        print(f"処理対象画像数: {len(image_paths)}件")
        
        # YOLO検出実行
        results = detect_boxes_with_yolo(
            image_paths, 
            args.model, 
            selected_class=args.class_name, 
            confidence=args.conf
        )
        
        # 結果を保存
        if results:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"検出結果をJSONに保存しました: {args.output_json}")
            print(f"検出成功画像数: {len(results)}件")
            return 0
        else:
            print("検出結果がありません")
            # 空のJSONを作成
            with open(args.output_json, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            return 1
        
    except Exception as e:
        print(f"エラー: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 