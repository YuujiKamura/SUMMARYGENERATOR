#!/usr/bin/env python3
"""
OCR結果表示ダイアログ
"""
import os
import json
import time
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QWidget, QSplitter, QGridLayout, QCheckBox, QTextEdit,
    QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QPixmap, QDrag, QPainter

# ドラッグ可能なコンポーネントをインポート
from src.widgets.draggable_components import DraggableGridTable, DraggableLabel, DropTextEdit


# OCR結果表示ダイアログ
class OcrResultsDialog(QDialog):
    """OCR結果を表示するダイアログ"""
    
    def __init__(self, ocr_results, parent=None):
        super().__init__(parent)
        self.ocr_results = ocr_results
        self.parent_app = parent
        self.setWindowTitle("Vision API OCR結果")
        self.resize(1200, 800)
        self.selected_items = []
        
        # ドラッグ操作用の変数
        self.dragged_text = ""
        
        # カスタムフィールド（グローバル辞書）
        self.default_fields = ["工種", "種別", "細別", "測点", "備考"]
        
        # グローバル辞書を読み込む
        loaded_dict = self.load_global_dictionary()
        
        # 既存の辞書がなければデフォルトフィールドで初期化
        if not loaded_dict:
            self.global_dictionary = {field: "" for field in self.default_fields}
        else:
            # 既存の辞書がある場合
            self.global_dictionary = loaded_dict
            
            # デフォルトフィールドが存在しない場合は追加
            for field in self.default_fields:
                if field not in self.global_dictionary:
                    self.global_dictionary[field] = ""
        
        # 画像ごとの辞書
        self.image_dictionaries = self.load_image_dictionaries() or {}
        
        # 現在表示中の画像パス
        self.current_image_path = None
        
        # グローバル辞書から単語リストを作成
        self.global_words = self.extract_global_dictionary_words()
        
        self.setup_ui()
    
    def extract_global_dictionary_words(self):
        """グローバル辞書から単語リストを抽出"""
        # カテゴリごとに単語を分類
        categorized_words = {
            "工種": set(),
            "種別": set(),
            "細別": set(),
            "測点": set(),
            "備考": set()
        }
        
        # 各フィールドの値を空白で分割して単語を抽出
        for field, value in self.global_dictionary.items():
            if value and field in categorized_words:
                for word in value.split():
                    categorized_words[field].add(word)
            elif value:  # カテゴリに含まれないフィールドの単語は備考に
                for word in value.split():
                    categorized_words["備考"].add(word)
        
        # 画像辞書からも単語を抽出
        for image_path, dictionary in self.image_dictionaries.items():
            for field, value in dictionary.items():
                if value and field in categorized_words:
                    for word in value.split():
                        categorized_words[field].add(word)
                elif value:  # カテゴリに含まれないフィールドの単語は備考に
                    for word in value.split():
                        categorized_words["備考"].add(word)
        
        # カテゴリごとにソートされた単語リスト
        result = {}
        for category, words in categorized_words.items():
            result[category] = sorted(list(words))
        
        # フラットなリストも保持（色の判定用）
        all_words = set()
        for words in categorized_words.values():
            all_words.update(words)
        
        return {"categorized": result, "all": sorted(list(all_words))}
    
    def setup_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # 余白を縮小
        
        # メインスプリッター（上下分割）
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === 上部：OCR結果リスト と グローバル辞書 ===
        top_container = QWidget()
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 上部スプリッター（左右分割）
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === 左上：OCR結果リスト ===
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)  # 余白を削除
        
        # 結果テーブル
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["選択", "サムネイル", "画像", "クラス", "OCRテキスト"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.results_table.setIconSize(QSize(120, 120))  # サムネイルサイズを大きく
        self.results_table.cellClicked.connect(self.on_result_clicked)
        
        list_layout.addWidget(self.results_table)
        
        # === 右上：グローバル辞書グリッド ===
        global_dict_widget = QWidget()
        global_dict_layout = QVBoxLayout(global_dict_widget)
        global_dict_layout.setContentsMargins(5, 5, 5, 5)
        
        global_dict_label = QLabel("グローバル辞書（ドラッグで単語グリッドに追加できます）")
        global_dict_layout.addWidget(global_dict_label)
        
        # グローバル辞書検索
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("辞書内検索...")
        self.search_edit.textChanged.connect(self.filter_global_dictionary)
        search_layout.addWidget(self.search_edit)
        
        self.refresh_dict_btn = QPushButton("更新")
        self.refresh_dict_btn.clicked.connect(self.refresh_global_dictionary)
        search_layout.addWidget(self.refresh_dict_btn)
        global_dict_layout.addLayout(search_layout)
        
        # グローバル辞書グリッド
        self.global_dict_grid = DraggableGridTable(5)  # 5列のグリッド
        self.global_dict_grid.set_parent_dialog(self)  # 親ダイアログを設定
        self.global_dict_grid.populate_categorized_words(self.global_words["categorized"])
        global_dict_layout.addWidget(self.global_dict_grid)
        
        # 上部スプリッターに追加
        top_splitter.addWidget(list_widget)
        top_splitter.addWidget(global_dict_widget)
        top_splitter.setSizes([700, 500])  # 初期サイズ
        
        top_layout.addWidget(top_splitter)
        
        # === 下部：グリッド表示 ===
        grid_container = QWidget()
        grid_container_layout = QHBoxLayout(grid_container)
        grid_container_layout.setContentsMargins(0, 0, 0, 0)  # 余白を削除
        
        # 下部スプリッター（左右分割）
        grid_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === 左側：単語グリッド ===
        word_grid_widget = QWidget()
        word_grid_layout = QVBoxLayout(word_grid_widget)
        word_grid_layout.setContentsMargins(5, 5, 5, 5)
        
        word_grid_label = QLabel("単語グリッド（ドラッグでキャプションに追加できます）")
        word_grid_layout.addWidget(word_grid_label)
        
        # ドラッグ可能な単語グリッド
        self.grid_table = DraggableGridTable(10)  # 10列のグリッド
        self.grid_table.set_parent_dialog(self)  # 親ダイアログを設定
        self.grid_table.setMinimumHeight(150)
        word_grid_layout.addWidget(self.grid_table)
        
        # === 右側：キャプショングリッド ===
        caption_widget = QWidget()
        caption_layout = QVBoxLayout(caption_widget)
        caption_layout.setContentsMargins(5, 5, 5, 5)
        
        caption_label = QLabel("キャプション設定（単語をドロップで追加）")
        caption_layout.addWidget(caption_label)
        
        # キャプションフィールド
        caption_form = QWidget()
        self.caption_layout = QGridLayout(caption_form)
        self.caption_layout.setContentsMargins(0, 0, 0, 0)
        
        # フィールドとドロップ領域を作成
        self.field_widgets = {}
        # 現在の画像パスがあればその辞書、なければグローバル辞書を使用
        dictionary_to_use = self.global_dictionary
        self.update_caption_fields(dictionary_to_use)
        
        caption_layout.addWidget(caption_form)
        caption_layout.addStretch()
        
        # スプリッターに追加（比率を調整）
        grid_splitter.addWidget(word_grid_widget)
        grid_splitter.addWidget(caption_widget)
        
        # 比率を設定（ユーザーのスクリーンショットに合わせる）
        total_width = 1000  # 任意の値
        grid_splitter.setSizes([total_width * 3 // 4, total_width // 4])  # 3:1の比率
        
        grid_container_layout.addWidget(grid_splitter)
        
        # メインスプリッターに追加
        main_splitter.addWidget(top_container)
        main_splitter.addWidget(grid_container)
        
        # メインスプリッターの比率設定
        main_splitter.setStretchFactor(0, 2)  # 上部を大きく
        main_splitter.setStretchFactor(1, 1)  # 下部を小さく
        
        layout.addWidget(main_splitter)
        
        # 閉じるボタンだけ残す
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # 右寄せにするためのスペーサー
        
        # 閉じるボタン
        close_btn = QPushButton("閉じる")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # 結果の表示
        self.populate_results()
    
    def filter_global_dictionary(self, text):
        """グローバル辞書を検索キーワードでフィルタリング"""
        if not text:
            # 検索キーワードがなければ全単語表示
            self.global_dict_grid.clear_grid()
            self.global_dict_grid.populate_categorized_words(self.global_words["categorized"])
            return
        
        # 検索キーワードに一致する単語をフィルタリング
        filtered_words = {}
        for category, words in self.global_words["categorized"].items():
            filtered = [word for word in words if text.lower() in word.lower()]
            if filtered:
                filtered_words[category] = filtered
        
        # グリッドを更新
        self.global_dict_grid.clear_grid()
        self.global_dict_grid.populate_categorized_words(filtered_words)
    
    def refresh_global_dictionary(self):
        """グローバル辞書の単語リストを更新"""
        # 単語リストを再抽出
        self.global_words = self.extract_global_dictionary_words()
        
        # グリッドを更新
        self.global_dict_grid.clear_grid()
        self.global_dict_grid.populate_categorized_words(self.global_words["categorized"])
        
        # 単語グリッドの色も更新
        if hasattr(self, 'grid_table') and self.grid_table:
            self.grid_table.update_word_colors()
        
        # 検索フィールドをクリア
        self.search_edit.clear()
        
        # 更新メッセージはコンソールに出力するだけ
        print("グローバル辞書を更新しました")
    
    def update_caption_fields(self, dictionary):
        """キャプションフィールドを更新"""
        # 既存のウィジェットをクリア
        for i in reversed(range(self.caption_layout.count())):
            item = self.caption_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        
        self.field_widgets = {}
        
        # フィールドとドロップ領域を作成
        for i, (field, value) in enumerate(dictionary.items()):
            # フィールド名ラベル
            self.caption_layout.addWidget(QLabel(f"{field}:"), i, 0)
            
            # ドロップ領域
            drop_area = DropTextEdit(self)
            drop_area.setAcceptDrops(True)
            drop_area.setText(value)
            drop_area.setMinimumWidth(300)
            drop_area.setMaximumHeight(80)
            drop_area.field_name = field  # フィールド名を記録
            drop_area.text_dropped.connect(self.on_text_dropped)
            self.field_widgets[field] = drop_area
            
            self.caption_layout.addWidget(drop_area, i, 1)
            
            # クリアボタン
            clear_btn = QPushButton("クリア")
            clear_btn.setMaximumWidth(60)
            clear_btn.clicked.connect(lambda checked, f=field: self.clear_field(f))
            self.caption_layout.addWidget(clear_btn, i, 2)
    
    def populate_results(self):
        """OCR結果をテーブルに表示"""
        row_count = 0
        
        # 各画像の結果を処理
        for image_path, result in self.ocr_results.items():
            image_name = os.path.basename(image_path)
            detections = result.get("detections", [])
            
            # 各検出結果をテーブルに追加
            for detection in detections:
                class_name = detection.get("class", "")
                ocr_text = detection.get("ocr_text", "").strip()
                
                # 空のOCRテキストはスキップ
                if not ocr_text:
                    continue
                
                # テーブルに行を追加
                self.results_table.insertRow(row_count)
                
                # チェックボックス
                checkbox = QCheckBox()
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.results_table.setCellWidget(row_count, 0, checkbox_widget)
                
                # サムネイル
                thumbnail = self.create_thumbnail(image_path, 120)  # サイズを大きく
                if thumbnail:
                    label = QLabel()
                    label.setPixmap(thumbnail)
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.results_table.setCellWidget(row_count, 1, label)
                
                # 画像名
                self.results_table.setItem(row_count, 2, QTableWidgetItem(image_name))
                
                # クラス名
                self.results_table.setItem(row_count, 3, QTableWidgetItem(class_name))
                
                # OCRテキスト
                self.results_table.setItem(row_count, 4, QTableWidgetItem(ocr_text))
                
                # データを保存（グリッド表示用）
                self.results_table.item(row_count, 4).setData(Qt.ItemDataRole.UserRole, {
                    "image_path": image_path,
                    "ocr_text": ocr_text,
                    "words": ocr_text.split()
                })
                
                row_count += 1
        
        # 行数が0の場合は「結果なし」メッセージを表示
        if row_count == 0:
            self.results_table.setRowCount(1)
            self.results_table.setSpan(0, 0, 1, 5)
            self.results_table.setItem(0, 0, QTableWidgetItem("OCRテキストが検出されませんでした"))
        
        # 行の高さを調整（サムネイルに合わせる）
        self.results_table.resizeRowsToContents()
    
    def on_result_clicked(self, row, column):
        """結果行がクリックされたときのハンドラ"""
        # OCRテキストアイテムを取得
        item = self.results_table.item(row, 4)
        if not item:
            return
        
        # ユーザーデータからテキストと単語リストを取得
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        words = data.get("words", [])
        image_path = data.get("image_path", "")
        
        # 現在の画像パスを更新
        self.current_image_path = image_path
        
        # 画像辞書を取得または初期化
        if image_path not in self.image_dictionaries:
            # 新しい画像の場合は空の辞書を作成（グローバル辞書のキーのみコピー）
            self.image_dictionaries[image_path] = {field: "" for field in self.global_dictionary.keys()}
            
            # グリーンの単語（グローバル辞書に存在する単語）を自動挿入
            if words:
                for word in words:
                    if word in self.global_words["all"]:
                        # 単語がどのカテゴリに属するか確認
                        category_found = False
                        for category, category_words in self.global_words["categorized"].items():
                            if word in category_words and category in self.image_dictionaries[image_path]:
                                # カテゴリが見つかったら対応するフィールドに追加
                                current_text = self.image_dictionaries[image_path][category]
                                if current_text:
                                    self.image_dictionaries[image_path][category] = f"{current_text} {word}"
                                else:
                                    self.image_dictionaries[image_path][category] = word
                                category_found = True
                                break
                        
                        # カテゴリが見つからなければ備考に追加
                        if not category_found and "備考" in self.image_dictionaries[image_path]:
                            current_text = self.image_dictionaries[image_path]["備考"]
                            if current_text:
                                self.image_dictionaries[image_path]["備考"] = f"{current_text} {word}"
                            else:
                                self.image_dictionaries[image_path]["備考"] = word
        
        # 画像辞書をUIに表示
        self.update_caption_fields(self.image_dictionaries[image_path])
        
        # グリッドテーブルをクリア
        self.grid_table.clear_grid()
        
        if not words:
            return
        
        # グリッドに単語を配置（グローバル辞書の単語リストも併せて渡す）
        self.grid_table.populate_words(words)
    
    def on_text_dropped(self, field_name, dropped_text):
        """テキストがドロップされたときのハンドラ"""
        if field_name not in self.field_widgets:
            return
            
        # 現在のテキストを取得
        current_text = self.field_widgets[field_name].toPlainText()
        
        # テキストを追加（すでにテキストがある場合は空白を挿入）
        if current_text:
            new_text = f"{current_text} {dropped_text}"
        else:
            new_text = dropped_text
        
        # テキストを設定
        self.field_widgets[field_name].setText(new_text)
        
        # 画像辞書に追加
        if self.current_image_path and self.current_image_path in self.image_dictionaries:
            self.image_dictionaries[self.current_image_path][field_name] = new_text
            
            # 変更を保存
            self.save_all_dictionaries()
            
            # グローバル辞書の単語リストを更新
            self.global_words = self.extract_global_dictionary_words()
            
            # グリッドの単語の色を更新
            self.grid_table.update_word_colors()
            
            # グローバル辞書グリッドも更新
            self.refresh_global_dictionary()
    
    def clear_field(self, field_name):
        """フィールドの内容をクリア"""
        if field_name not in self.field_widgets:
            return
            
        self.field_widgets[field_name].clear()
        
        # 画像辞書をクリア
        if self.current_image_path and self.current_image_path in self.image_dictionaries:
            self.image_dictionaries[self.current_image_path][field_name] = ""
            
            # 変更を保存
            self.save_all_dictionaries()
            
            # グローバル辞書の単語リストを更新
            self.global_words = self.extract_global_dictionary_words()
            
            # グリッドの単語の色を更新
            self.grid_table.update_word_colors()
            
            # グローバル辞書グリッドも更新
            self.refresh_global_dictionary()
    
    def load_global_dictionary(self):
        """グローバル辞書を読み込む"""
        try:
            dict_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "global_dictionary.json")
            if os.path.exists(dict_file):
                with open(dict_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"グローバル辞書読み込みエラー: {e}")
        return None
    
    def save_global_dictionary(self):
        """グローバル辞書を保存する"""
        try:
            # 保存
            dict_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "global_dictionary.json")
            os.makedirs(os.path.dirname(dict_file), exist_ok=True)
            
            with open(dict_file, 'w', encoding='utf-8') as f:
                json.dump(self.global_dictionary, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"グローバル辞書保存エラー: {e}")
            return False
    
    def load_image_dictionaries(self):
        """画像ごとの辞書を読み込む"""
        try:
            dict_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "image_dictionaries.json")
            if os.path.exists(dict_file):
                with open(dict_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"画像辞書読み込みエラー: {e}")
        return None
    
    def save_image_dictionaries(self):
        """画像ごとの辞書を保存する"""
        try:
            # 現在表示中の画像辞書を更新
            if self.current_image_path and self.current_image_path in self.image_dictionaries:
                for field, widget in self.field_widgets.items():
                    self.image_dictionaries[self.current_image_path][field] = widget.toPlainText()
            
            # 保存
            dict_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "image_dictionaries.json")
            os.makedirs(os.path.dirname(dict_file), exist_ok=True)
            
            with open(dict_file, 'w', encoding='utf-8') as f:
                json.dump(self.image_dictionaries, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"画像辞書保存エラー: {e}")
            return False
    
    def save_all_dictionaries(self):
        """全ての辞書を保存する"""
        # 現在表示中の辞書を更新
        if self.current_image_path and self.current_image_path in self.image_dictionaries:
            for field, widget in self.field_widgets.items():
                self.image_dictionaries[self.current_image_path][field] = widget.toPlainText()
        
        # 画像辞書を保存
        image_saved = self.save_image_dictionaries()
        
        if not image_saved:
            print("画像辞書の保存に失敗しました")
        else:
            print("画像辞書を保存しました")
    
    def select_all_items(self):
        """全ての項目を選択"""
        for row in range(self.results_table.rowCount()):
            checkbox_widget = self.results_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def deselect_all_items(self):
        """全ての項目の選択を解除"""
        for row in range(self.results_table.rowCount()):
            checkbox_widget = self.results_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    
    def copy_grid_items(self):
        """グリッドの単語をコピー"""
        selected_words = self.grid_table.get_selected_words()
        
        if selected_words:
            clipboard_text = " ".join(selected_words)
            QApplication.clipboard().setText(clipboard_text)
            self.status_message("単語をクリップボードにコピーしました")
        else:
            self.status_message("単語がありません")
    
    def create_thumbnail(self, image_path, size=120):
        """画像からサムネイルを作成"""
        if not os.path.exists(image_path):
            return None
        
        try:
            # 親アプリケーションのサムネイル作成メソッドを使用
            if hasattr(self.parent_app, 'create_thumbnail'):
                return self.parent_app.create_thumbnail(image_path, size)
            
            # 親アプリケーションにメソッドがない場合は独自に実装
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return None
            
            return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception as e:
            print(f"サムネイル作成エラー: {e}")
            return None
    
    def status_message(self, message):
        """ステータスメッセージを表示（コンソール出力のみ）"""
        print(message)
    
    def closeEvent(self, event):
        """ダイアログが閉じられるときの処理"""
        # すべての辞書を保存
        self.save_all_dictionaries()
        event.accept()
    
    def hideEvent(self, event):
        """ダイアログが非表示になる時の処理"""
        # すべての辞書を保存
        self.save_all_dictionaries()
        super().hideEvent(event)
    
    def moveEvent(self, event):
        """ダイアログが移動する時の処理"""
        # イベントをフィルタリングして負荷を軽減
        if hasattr(self, "_last_move_time"):
            if time.time() - self._last_move_time < 5.0:  # 5秒間隔でのみ保存
                super().moveEvent(event)
                return
        
        # すべての辞書を保存
        self.save_all_dictionaries()
        self._last_move_time = time.time()
        
        super().moveEvent(event)
    
    def from_imported_class(self):
        """このクラスが正しくインポートされたことを確認するためのメソッド"""
        return "OcrResultsDialog successfully imported" 