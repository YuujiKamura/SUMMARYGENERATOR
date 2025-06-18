from caption_board_ocr_filter import should_skip_ocr_by_size_and_aspect

def test_case():
    width = 1226
    height = 863
    area = 1226 * 863
    result = should_skip_ocr_by_size_and_aspect(width, height, area, min_area=100_000)
    print(f"入力: width={width}, height={height}, area={area}")
    print(f"スキップ判定: {result['skip']}, 理由: {result['reason']}")

if __name__ == "__main__":
    test_case()
