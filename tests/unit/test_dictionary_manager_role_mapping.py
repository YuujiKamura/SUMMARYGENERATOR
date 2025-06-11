# テスト: DictionaryManagerのロール逆引きマッチングAPI
import pytest
from src.dictionary_manager import DictionaryManager

def test_match_remarks_by_roles_any():
    dm = DictionaryManager(db_path=None)
    # テスト用role_mappingsを直接セット
    dm.role_mappings = {
        "出来形": {"roles": ["caption_board_thermometer"], "match": "any"},
        "端部乳剤塗布状況": {"roles": ["role_worker_emulsion_edge"], "match": "all"},
        "積込状況": {"roles": ["role_driver_backhoe_pavement_load", "truck_4t_loading_crushed_asphalt"], "match": "any"}
    }
    # any: 1つでも含めばOK
    assert set(dm.match_remarks_by_roles(["caption_board_thermometer"])) == {"出来形"}
    assert set(dm.match_remarks_by_roles(["role_driver_backhoe_pavement_load"])) == {"積込状況"}
    assert set(dm.match_remarks_by_roles(["truck_4t_loading_crushed_asphalt"])) == {"積込状況"}
    # 両方含めば両方返る
    assert set(dm.match_remarks_by_roles(["caption_board_thermometer", "role_driver_backhoe_pavement_load"])) == {"出来形", "積込状況"}

def test_match_remarks_by_roles_all():
    dm = DictionaryManager(db_path=None)
    dm.role_mappings = {
        "A": {"roles": ["r1", "r2"], "match": "all"},
        "B": {"roles": ["r2", "r3"], "match": "all"}
    }
    # all: 全て含まないとマッチしない
    assert dm.match_remarks_by_roles(["r1", "r2"]) == ["A"]
    assert dm.match_remarks_by_roles(["r2", "r3"]) == ["B"]
    assert dm.match_remarks_by_roles(["r1"]) == []
    assert dm.match_remarks_by_roles(["r2"]) == []
    assert dm.match_remarks_by_roles(["r1", "r2", "r3"]) == ["A", "B"]

def test_match_remarks_by_roles_override_match_mode():
    dm = DictionaryManager(db_path=None)
    dm.role_mappings = {
        "C": {"roles": ["r1", "r2"], "match": "all"}
    }
    # match_modeでanyを強制
    assert dm.match_remarks_by_roles(["r1"], match_mode="any") == ["C"]
    assert dm.match_remarks_by_roles(["r2"], match_mode="any") == ["C"]
    assert dm.match_remarks_by_roles(["r1", "r2"], match_mode="any") == ["C"]
    # match_modeでallを強制
    assert dm.match_remarks_by_roles(["r1"], match_mode="all") == []
    assert dm.match_remarks_by_roles(["r1", "r2"], match_mode="all") == ["C"]
