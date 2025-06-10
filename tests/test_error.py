#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト機能の確認用テスト
"""
import pytest
import os
import sys

@pytest.mark.unit
def test_simple_calculation():
    """シンプルな計算のテスト"""
    value = (1 + 2) * 3
    assert value == 9

@pytest.mark.unit
def test_string_operation():
    """文字列操作のテスト"""
    text = "Hello" + " " + "World"
    assert text == "Hello World"

# テストを追加
def test_boolean_operation():
    """ブール演算のテスト"""
    assert True and True 
    assert not False

@pytest.mark.unit
def test_module_import():
    """モジュールインポートのテスト"""
    # 標準モジュールをインポート
    import json
    import datetime
    
    # 日付をJSONに変換できることを確認
    now = datetime.datetime.now()
    now_str = json.dumps(now.isoformat())
    assert isinstance(now_str, str)
    assert "T" in now_str  # ISO形式の日付には'T'が含まれる 