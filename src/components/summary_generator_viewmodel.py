from PyQt6.QtCore import QObject, pyqtSignal
import logging
logger = logging.getLogger(__name__)

class SummaryGeneratorViewModel(QObject):
    image_list_changed = pyqtSignal(list)
    remarks_changed = pyqtSignal(list)  # ChainRecordのリストをemitする
    status_changed = pyqtSignal(str)

    def __init__(self, data_service=None):
        super().__init__()
        self.data_service = data_service
        self.images = []
        self.remarks = []  # ChainRecordのリストで統一
        self.status = ""

    def load_images(self, folder):
        logger.info('画像リスト取得: folder=%s', folder)
        if self.data_service:
            images = self.data_service.get_image_list(folder)
            logger.debug('画像リスト取得: 件数=%d', len(images) if images else 0)
            self.images = images
        else:
            self.images = []
        self.image_list_changed.emit(self.images)

    def select_image(self, img_path):
        logger.info('画像選択: img_path=%s', img_path)
        if self.data_service:
            entry = self.data_service.get_image_entry_for_image(img_path)
            logger.debug('ImageEntry取得: %s', entry)
            if entry and hasattr(entry, 'chain_records'):
                self.remarks = entry.chain_records
                logger.debug('chain_records件数: %d', len(self.remarks))
            else:
                self.remarks = []
                logger.debug('chain_recordsなし')
        else:
            self.remarks = []
        self.remarks_changed.emit(self.remarks)

    def set_status(self, msg):
        logger.info('ステータス更新: %s', msg)
        self.status = msg
        self.status_changed.emit(msg)
