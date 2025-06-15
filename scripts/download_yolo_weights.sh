#!/usr/bin/env bash
# YOLOv8 重みファイルをダウンロードする簡易スクリプト
set -e
MODEL_DIR="$(dirname "${BASH_SOURCE[0]}")/../src/yolo/weights"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

if [ ! -f yolov8n.pt ]; then
  echo "[INFO] Download yolov8n.pt"
  curl -L -o yolov8n.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
else
  echo "[SKIP] yolov8n.pt already exists"
fi

echo "[INFO] YOLO weights are ready in $MODEL_DIR" 