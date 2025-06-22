import pytest
from src.dekigata_judge import judge_dekigata_remarks

def fake_record(bboxes=None, img_w=1000, img_h=1000):
    # ダミーのChainRecord/dict
    return {
        'roles': ['caption_board_dekigata'],
        'bboxes': bboxes or [
            {'role': 'caption_board', 'bbox': [100, 100, 900, 900]},
        ],
        'img_w': img_w,
        'img_h': img_h,
    }

def test_judge_dekigata_remarks_closeup():
    # 大きなボード（接写）
    record = fake_record(bboxes=[{'role': 'caption_board', 'bbox': [0, 0, 1000, 1000]}])
    mapping = ['出来形全景', '出来形接写', '出来形管理値']
    result = judge_dekigata_remarks(record['roles'], mapping, record=record)
    assert result and '接写' in result[0]

def test_judge_dekigata_remarks_overview():
    # 小さなボード（全景）
    record = fake_record(bboxes=[{'role': 'caption_board', 'bbox': [100, 100, 300, 300]}])
    mapping = ['出来形全景', '出来形接写', '出来形管理値']
    result = judge_dekigata_remarks(record['roles'], mapping, record=record)
    assert result and '全景' in result[0]

def test_judge_dekigata_remarks_kanrichi():
    # 超大きなボード（管理値）
    record = fake_record(bboxes=[{'role': 'caption_board', 'bbox': [0, 0, 1000, 1000]}], img_w=1000, img_h=1000)
    mapping = ['出来形全景', '出来形接写', '出来形管理値']
    # threshold_kanrichiを超える場合を模擬
    # judge_caption_board_closeupのデフォルト閾値に依存
    result = judge_dekigata_remarks(record['roles'], mapping, record=record)
    # 管理値判定はNone返却仕様なので、mappingに"管理値"が含まれていればOK
    assert result and '管理値' in result[0]

def test_judge_dekigata_remarks_no_caption():
    # caption_boardがない場合
    record = fake_record(bboxes=[])
    mapping = ['出来形全景', '出来形接写', '出来形管理値']
    result = judge_dekigata_remarks(record['roles'], mapping, record=record)
    assert result == []
