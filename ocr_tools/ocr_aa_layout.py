import unicodedata

def get_display_width(text):
    """全角・半角を考慮した表示幅を返す（曖昧幅は1幅扱い）"""
    width = 0
    for c in text:
        if unicodedata.east_asian_width(c) in 'FW':  # 'A'は1幅扱い
            width += 2
        else:
            width += 1
    return width

def pad_to_width(text, width):
    """全角・半角を考慮してwidth分だけ左詰め"""
    current = get_display_width(text)
    return text + ' ' * (width - current)

def truncate_to_display_width(text, max_width):
    """全角・半角を考慮してmax_width分だけ切り詰める"""
    result = ""
    width = 0
    for c in text:
        w = 2 if unicodedata.east_asian_width(c) in 'FWA' else 1
        if width + w > max_width:
            break
        result += c
        width += w
    return result

def print_ocr_aa_layout(texts_with_boxes, image_width, image_height, cell_size=32, cell_disp_width=2, highlight_boxes=None):
    """
    OCR結果のテキスト＋座標リストをAA風に2次元配置してprintする（セル内はcell_disp_width分だけ）
    texts_with_boxes: [{'text': str, 'x': int, 'y': int}, ...]
    image_width, image_height: 画像サイズ
    cell_size: セルの1辺のピクセル数（デフォルト32）
    cell_disp_width: セルの表示幅（デフォルト4）
    highlight_boxes: [{'x': int, 'y': int}, ...] 検出キーワードの座標リスト（省略可）
    """
    cols = image_width // cell_size
    rows = image_height // cell_size
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    for item in texts_with_boxes:
        x, y = item.get('x'), item.get('y')
        text = item.get('text', '').replace('\n', '').replace(' ', '')
        if x is None or y is None or not text:
            continue
        col = min(x // cell_size, cols - 1)
        row = min(y // cell_size, rows - 1)
        if not grid[row][col]:
            grid[row][col] = text
    # ハイライト対象セルのセットを作成
    highlight_cells = set()
    if highlight_boxes:
        for box in highlight_boxes:
            x, y = box.get('x'), box.get('y')
            if x is not None and y is not None:
                col = min(x // cell_size, cols - 1)
                row = min(y // cell_size, rows - 1)
                highlight_cells.add((row, col))
    for row_idx in range(rows):
        # 1. アドレス列を初期化
        line = []
        for col in range(cols):
            line.append('|')  # 区切り記号を縦棒に
            line.extend([' '] * cell_disp_width)  # セル幅分の空白
        line.append('|')  # 行末の区切り記号
        # 2. その行にある文字列をアドレス上に上書き
        for col in range(cols):
            text = grid[row_idx][col]
            if text:
                start = col * (cell_disp_width + 1) + 1  # 区切り記号の直後
                w = 0
                for c in text:
                    cw = get_display_width(c)
                    # 右側の空白や区切り記号を先に消す
                    for k in range(1, cw):
                        if start + w + k < len(line):
                            line[start + w + k] = ''
                    # 左側（開始位置）に文字を入れる
                    if start + w < len(line):
                        line[start + w] = c
                    w += cw
        # 3. ハイライトセルがあれば、そのセルの2バイト分左に▶を描画
        if highlight_cells:
            for col in range(cols):
                if (row_idx, col) in highlight_cells:
                    start = col * (cell_disp_width + 1) + 1
                    arrow_pos = max(0, start - 2)  # 2バイト分左
                    line[arrow_pos] = '▶'
        print(''.join(line).rstrip())

# この行を削除またはコメントアウト
# print_ocr_aa_layout(texts_with_boxes, image_width, image_height, cell_size=64, cell_disp_width=8) 