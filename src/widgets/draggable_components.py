#!/usr/bin/env python3
"""
ドラッグ可能なUIコンポーネント
"""
import sys
from PyQt6.QtWidgets import (
    QTableWidget, QHeaderView, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QTextEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QMimeData
from PyQt6.QtGui import QDrag, QPainter, QPixmap


# ドラッグ可能な単語グリッドテーブル
class DraggableGridTable(QTableWidget):
    """ドラッグ操作が可能な単語グリッドテーブル"""
    
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setColumnCount(columns)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        
        # 列の幅を内容に合わせて設定（Stretchから変更）
        for i in range(columns):
            self.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # ドラッグ開始を有効化
        self.setDragEnabled(True)
        
        # 親ダイアログへの参照（グローバル辞書アクセス用）
        self.parent_dialog = None
    
    def set_parent_dialog(self, dialog):
        """親ダイアログを設定"""
        self.parent_dialog = dialog
    
    def clear_grid(self):
        """グリッドをクリア"""
        self.clear()
        self.setRowCount(0)
    
    def populate_words(self, words):
        """単語をグリッドに配置"""
        if not words:
            return
            
        cols = self.columnCount()
        rows = (len(words) + cols - 1) // cols  # 必要な行数を計算
        
        self.setRowCount(rows)
        
        # グローバル辞書の単語リストを取得
        global_words = []
        if self.parent_dialog and hasattr(self.parent_dialog, "global_words"):
            global_words = self.parent_dialog.global_words.get("all", [])
        
        # ドラッグ可能なラベルを配置
        for i, word in enumerate(words):
            row = i // cols
            col = i % cols
            
            # ドラッグ可能なラベルセルを作成
            cell_widget = QWidget()
            cell_layout = QVBoxLayout(cell_widget)
            cell_layout.setContentsMargins(2, 2, 2, 2)
            
            # 単語がグローバル辞書にあるかチェック
            in_dictionary = word in global_words
            
            word_label = DraggableLabel(word, in_dictionary)
            # 長い単語のために最小幅を設定
            word_label.setMinimumWidth(len(word) * 8)  # 文字あたり約8ピクセル
            
            cell_layout.addWidget(word_label)
            self.setCellWidget(row, col, cell_widget)
        
        # すべてのセルが追加された後にテーブルを調整
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
    
    def populate_categorized_words(self, categorized_words):
        """カテゴリごとに分類された単語をグリッドに配置"""
        if not categorized_words:
            return
        
        # カテゴリの表示順序を定義
        category_order = ["工種", "種別", "細別", "測点", "備考"]
        
        cols = self.columnCount()
        total_rows = 0
        
        # カテゴリごとの行数を計算
        for category in category_order:
            if category in categorized_words and categorized_words[category]:
                words = categorized_words[category]
                category_rows = (len(words) + cols - 1) // cols  # カテゴリ内の必要な行数
                total_rows += category_rows + 1  # カテゴリの行 + 単語の行
        
        self.setRowCount(total_rows)
        
        # グローバル辞書の単語リストを取得（色設定用）
        global_words = []
        if self.parent_dialog and hasattr(self.parent_dialog, "global_words"):
            global_words = self.parent_dialog.global_words.get("all", [])
        
        current_row = 0
        
        # カテゴリごとに配置
        for category in category_order:
            if category not in categorized_words or not categorized_words[category]:
                continue
                
            words = categorized_words[category]
            
            # カテゴリ行を作成
            self.setSpan(current_row, 0, 1, cols)  # 行全体をスパン
            
            category_widget = QWidget()
            category_layout = QHBoxLayout(category_widget)
            category_layout.setContentsMargins(5, 3, 5, 3)
            
            category_label = QLabel(f"【{category}】")
            category_label.setStyleSheet("font-weight: bold; color: #333; background-color: #e0e0e0;")
            category_layout.addWidget(category_label)
            
            self.setCellWidget(current_row, 0, category_widget)
            current_row += 1
            
            # 単語を配置
            for i, word in enumerate(words):
                col = i % cols
                if col == 0 and i > 0:
                    current_row += 1
                
                # ドラッグ可能なラベルセルを作成
                cell_widget = QWidget()
                cell_layout = QVBoxLayout(cell_widget)
                cell_layout.setContentsMargins(2, 2, 2, 2)
                
                # 単語がグローバル辞書にあるかチェック
                in_dictionary = word in global_words
                
                word_label = DraggableLabel(word, in_dictionary)
                # 長い単語のために最小幅を設定
                word_label.setMinimumWidth(len(word) * 8)  # 文字あたり約8ピクセル
                
                cell_layout.addWidget(word_label)
                self.setCellWidget(current_row, col, cell_widget)
            
            current_row += 1
        
        # すべてのセルが追加された後にテーブルを調整
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
    
    def update_word_colors(self):
        """単語の色を更新"""
        if not self.parent_dialog or not hasattr(self.parent_dialog, "global_words"):
            return
            
        # グローバル辞書の単語リストを取得
        global_words = self.parent_dialog.global_words.get("all", [])
        
        # すべてのセルを確認
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    label = cell_widget.findChild(DraggableLabel)
                    if label:
                        # 単語がグローバル辞書にあるかチェック
                        in_dictionary = label.text() in global_words
                        label.set_in_dictionary(in_dictionary)
    
    def get_selected_words(self):
        """選択された単語のリストを取得"""
        # チェックボックスが不要になったため、すべての単語を返す
        words = []
        
        for row in range(self.rowCount()):
            for col in range(self.columnCount()):
                cell_widget = self.cellWidget(row, col)
                if cell_widget:
                    label = cell_widget.findChild(DraggableLabel)
                    if label:
                        words.append(label.text())
        
        return words


# ドラッグ可能なラベル
class DraggableLabel(QLabel):
    """ドラッグ操作が可能なラベル"""
    
    def __init__(self, text, in_dictionary=False, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(False)  # 自分自身へのドロップは不要
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.in_dictionary = in_dictionary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 状態に応じた背景色を設定
        self.update_style()
        
        # テキストに合わせてサイズを調整
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(text) + 20  # 余白を追加
        self.setMinimumWidth(text_width)
        
        # セルサイズの調整のために高さも設定
        self.setMinimumHeight(32)
        
        # 長いテキストに対応するために単語ラップを有効化
        self.setWordWrap(True)
    
    def set_in_dictionary(self, in_dict):
        """辞書内かどうかを設定"""
        if self.in_dictionary != in_dict:
            self.in_dictionary = in_dict
            self.update_style()
    
    def update_style(self):
        """状態に応じてスタイルを更新"""
        if self.in_dictionary:
            # グローバル辞書に存在する単語 - 緑色
            self.setStyleSheet("background-color: #c8e6c9; border-radius: 4px; padding: 6px; margin: 2px;")
        else:
            # グローバル辞書に存在しない単語 - 赤色
            self.setStyleSheet("background-color: #ffcdd2; border-radius: 4px; padding: 6px; margin: 2px;")
    
    def mousePressEvent(self, event):
        """マウスボタンが押された時のイベント"""
        super().mousePressEvent(event)
        
        # 左ボタンの場合のみドラッグを考慮
        if event.button() == Qt.MouseButton.LeftButton:
            # ドラッグ開始位置を記録
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        """マウスが移動した時のイベント"""
        # 左ボタンが押されているか確認
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
            
        # 最小ドラッグ距離をチェック
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        # ドラッグ操作を開始
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.text())
        drag.setMimeData(mime_data)
        
        # ドラッグ中の表示を設定
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        self.render(painter)
        painter.end()
        drag.setPixmap(pixmap)
        
        # ドラッグ操作を実行
        drag.exec(Qt.DropAction.CopyAction)


# ドロップ可能なテキスト編集エリア
class DropTextEdit(QTextEdit):
    """テキストのドロップを受け付けるテキスト編集エリア"""
    
    # カスタムシグナル
    text_dropped = pyqtSignal(str, str)  # フィールド名, ドロップされたテキスト
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.field_name = ""  # 関連付けられたフィールド名
    
    def dragEnterEvent(self, event):
        """ドラッグがエリアに入った時のイベント"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event):
        """ドラッグがエリア内を移動した時のイベント"""
        if event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        """ドロップされた時のイベント"""
        if event.mimeData().hasText():
            # ドロップされたテキストを取得
            text = event.mimeData().text()
            
            # シグナルを発行
            self.text_dropped.emit(self.field_name, text)
            
            event.acceptProposedAction() 