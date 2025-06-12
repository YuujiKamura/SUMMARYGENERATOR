class QMessageBox:
    class StandardButton:
        Yes = 1
        No = 0

    @staticmethod
    def question(*args, **kwargs):
        return QMessageBox.StandardButton.Yes

class QApplication:
    def __init__(self, *args, **kwargs):
        pass
    @staticmethod
    def instance():
        return None
