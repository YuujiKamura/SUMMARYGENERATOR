from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer

def warning_with_timeout(parent, title, message, timeout=2000):
    box = QMessageBox(QMessageBox.Icon.Warning, title, message, QMessageBox.StandardButton.Ok, parent)
    QTimer.singleShot(timeout, box.accept)
    return box.exec()

def critical_with_timeout(parent, title, message, timeout=2000):
    box = QMessageBox(QMessageBox.Icon.Critical, title, message, QMessageBox.StandardButton.Ok, parent)
    QTimer.singleShot(timeout, box.accept)
    return box.exec()
