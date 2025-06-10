#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テストマネージャの機能テスト用単純テストケース
"""
import sys
import os
import pytest

def test_simple_addition():
    """単純な足し算のテスト"""
    assert 1 + 1 == 2

def test_simple_subtraction():
    """単純な引き算のテスト"""
    assert 3 - 1 == 2

class TestSimpleClass:
    """シンプルなテストクラス"""
    
    def test_multiplication(self):
        """掛け算のテスト"""
        assert 2 * 3 == 6
    
    def test_division(self):
        """割り算のテスト"""
        assert 6 / 2 == 3 