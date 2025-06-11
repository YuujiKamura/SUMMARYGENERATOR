#!/usr/bin/env python3
"""
アプリケーション設定の保存と読み込みを行うモジュール
"""
import os
import json
from PyQt6.QtWidgets import QComboBox, QSpinBox, QLineEdit, QSlider

# デフォルトの設定ファイルパス
DEFAULT_SETTINGS_FILE = "yolo_manager_settings.json"
DEFAULT_CLASSES_FILE = "auto_annotate_classes.json"

class SettingsManager:
    """アプリケーション設定の管理クラス"""
    
    def __init__(self, settings_file=DEFAULT_SETTINGS_FILE, classes_file=DEFAULT_CLASSES_FILE):
        """
        初期化
        
        Args:
            settings_file (str): 設定ファイルのパス
            classes_file (str): クラス設定ファイルのパス
        """
        self.settings_file = settings_file
        self.classes_file = classes_file
    
    def save_settings(self, ui_components, console_output=None):
        """
        UIコンポーネントから設定を保存
        
        Args:
            ui_components (dict): UI要素の辞書 {"name": component}
            console_output (callable, optional): コンソール出力関数
            
        Returns:
            bool: 保存の成功/失敗
        """
        settings = {}
        
        # UIコンポーネントから値を取得
        for key, component in ui_components.items():
            # テスト環境対応：ダミーコンポーネントの場合
            if hasattr(component, "_value"):
                settings[key] = component._value
            elif isinstance(component, QComboBox):
                settings[key] = component.currentText()
            elif isinstance(component, QSpinBox):
                settings[key] = component.value()
            elif isinstance(component, QLineEdit):
                settings[key] = component.text()
            elif isinstance(component, QSlider):
                settings[key] = component.value()
            else:
                # その他の値はそのまま保存を試みる
                try:
                    settings[key] = component
                except:
                    pass
        
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            if console_output:
                console_output(f"設定を保存しました: {self.settings_file}")
            return True
        
        except Exception as e:
            if console_output:
                console_output(f"設定の保存に失敗しました: {e}")
            return False
    
    def load_settings(self, ui_components, console_output=None):
        """
        設定ファイルを読み込みUIコンポーネントに適用
        
        Args:
            ui_components (dict): UI要素の辞書 {"name": component}
            console_output (callable, optional): コンソール出力関数
            
        Returns:
            dict: 読み込まれた設定、失敗時は空辞書
        """
        if not os.path.exists(self.settings_file):
            if console_output:
                console_output(f"設定ファイルが見つかりません: {self.settings_file}")
            return {}
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # UIコンポーネントに値を適用
            for key, value in settings.items():
                if key in ui_components:
                    component = ui_components[key]
                    
                    # テスト環境対応：ダミーコンポーネントの場合
                    if hasattr(component, "setValue"):
                        component.setValue(value)
                    elif hasattr(component, "setText"):
                        component.setText(value)
                    elif isinstance(component, QComboBox):
                        index = component.findText(value)
                        if index >= 0:
                            component.setCurrentIndex(index)
                        elif value and os.path.exists(value):
                            # コンボボックスに存在しないが、ファイルが存在する場合は追加
                            component.addItem(value)
                            component.setCurrentIndex(component.count() - 1)
            
            if console_output:
                console_output(f"設定を読み込みました: {self.settings_file}")
            return settings
        
        except Exception as e:
            if console_output:
                console_output(f"設定の読み込みに失敗しました: {e}")
            return {}
    
    def save_class_settings(self, classes_dict, console_output=None):
        """
        検出クラス設定を保存
        
        Args:
            classes_dict (dict): 検出クラス辞書 {プロンプト: クラス名}
            console_output (callable, optional): コンソール出力関数
            
        Returns:
            bool: 保存の成功/失敗
        """
        try:
            with open(self.classes_file, 'w', encoding='utf-8') as f:
                json.dump(classes_dict, f, ensure_ascii=False, indent=2)
            
            if console_output:
                console_output(f"検出クラス設定を保存しました: {self.classes_file}")
            return True
        
        except Exception as e:
            if console_output:
                console_output(f"検出クラス設定の保存に失敗しました: {e}")
            return False
    
    def load_class_settings(self, console_output=None):
        """
        検出クラス設定を読み込み
        
        Args:
            console_output (callable, optional): コンソール出力関数
            
        Returns:
            dict: 読み込まれたクラス設定、失敗時は空辞書
        """
        if not os.path.exists(self.classes_file):
            # デフォルトのクラス設定
            default_classes = {
                "管理図ボード": "board",
                "標尺ロッド": "rod",
                "作業員": "worker"
            }
            
            # 最初の実行時はデフォルト設定を保存
            try:
                with open(self.classes_file, 'w', encoding='utf-8') as f:
                    json.dump(default_classes, f, ensure_ascii=False, indent=2)
                
                if console_output:
                    console_output(f"デフォルトの検出クラス設定を作成しました: {self.classes_file}")
                
                return default_classes
            except:
                pass
            
            return default_classes
        
        try:
            with open(self.classes_file, 'r', encoding='utf-8') as f:
                classes_dict = json.load(f)
            
            if console_output:
                console_output(f"検出クラス設定を読み込みました: {self.classes_file}")
            
            return classes_dict
        
        except Exception as e:
            if console_output:
                console_output(f"検出クラス設定の読み込みに失敗しました: {e}")
            return {} 