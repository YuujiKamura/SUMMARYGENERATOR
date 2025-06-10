"""
Cursor/Copilotへのプロンプト送信自動化スクリプト
パスマネージャー経由でパス管理を徹底すること。
"""
import sys
import time
import argparse
import pyautogui
import pyperclip
# --- パスマネージャー徹底ルール ---
# 画像・データ・DB等のパスは必ず
# src/utils/path_manager.pyのPathManager経由で取得すること。
# 直書き・os.path.join等の手動生成は禁止。
# 例: image_preview_cache_master.jsonのパス取得
# master_json_path = path_manager.get_cache_json(
#     "image_preview_cache_master.json"
# )
from src.utils.path_manager import path_manager
_ = path_manager  # ルール徹底のためダミー参照

# --- 設定 ---
CURSOR_PROMPT_X = 1605  # Cursorプロンプト入力欄のX座標（右）
CURSOR_PROMPT_Y = 936   # Cursorプロンプト入力欄のY座標（右）
COPILOT_PROMPT_X = 688  # Copilotプロンプト入力欄のX座標（左）
COPILOT_PROMPT_Y = 943  # Copilotプロンプト入力欄のY座標（左）

# --- argparseでコマンドライン引数をパース ---
parser = argparse.ArgumentParser()
parser.add_argument('text', nargs='?', default=None, help='送信するテキスト')
parser.add_argument('--to', dest='to', default=None, help='送信先 (cursor/copilot)')
parser.add_argument('--from', dest='sender', default=None, help='送信者名')
args, unknown = parser.parse_known_args()

SEND_TO = args.to.lower() if args.to else 'cursor'
SENDER_NAME = args.sender if args.sender else (
    'GitHub Copilot' if SEND_TO == 'copilot' else 'Cursor'
)
# 送信先と送信者が同じ場合は自動で片方を切り替え
if SEND_TO == SENDER_NAME.lower():
    SENDER_NAME = 'Cursor' if SEND_TO == 'copilot' else 'GitHub Copilot'
    print(
        f"[警告] 送信先と送信者が同じだったため、"
        f"送信者を自動で '{SENDER_NAME}' に変更しました。"
    )

if SEND_TO == 'cursor':
    CLICK_X, CLICK_Y = CURSOR_PROMPT_X, CURSOR_PROMPT_Y
elif SEND_TO == 'copilot':
    CLICK_X, CLICK_Y = COPILOT_PROMPT_X, COPILOT_PROMPT_Y
else:
    CLICK_X, CLICK_Y = CURSOR_PROMPT_X, CURSOR_PROMPT_Y  # fallback

# --- 1. 入力欄をクリックしてフォーカス ---
pyautogui.click(CLICK_X, CLICK_Y)
time.sleep(0.5)

# --- 送信内容をコマンドライン引数から取得 ---
if args.text:
    text = args.text
else:
    print(
        "[エラー] 送信内容はコマンドライン引数で指定してください。"
        "例: python send_prompt.py 'メッセージ' --to cursor"
    )
    sys.exit(1)

# --- プロンプト内容に送信者名・宛先名を追加 ---
if text.strip().startswith('[From'):
    prompt_content = text.replace('\n', ' ')
else:
    prompt_content = (
        f"[From {SENDER_NAME}][To {SEND_TO.capitalize()}] "
        + text.replace('\n', ' ')
    )

# --- 入力方法をクリップボード経由に統一 ---
pyperclip.copy(prompt_content)
time.sleep(1.0)
clipboard_content = pyperclip.paste()
print(f"[DEBUG] クリップボード内容: {clipboard_content[:100]}...")
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.2)
pyautogui.press('enter')

# 例: Copilotへの並列作業指示用プロンプト
# python send_prompt.py \
#   "今後はCLIで拡張YOLOデータセット作成＋学習を自動化します。\nCopilot側はUIや他のタスクと並列で作業を進めてください。" \
#   --to copilot --from cursor
