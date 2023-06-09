import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QPushButton, QGridLayout, QDateEdit, QFileDialog, QMessageBox, QListWidgetItem,
    QLabel, QGestureEvent, QPinchGesture
)
from PyQt5.QtCore import Qt, QSize, QDate, QPointF, QEvent, QByteArray, QBuffer
from PyQt5.QtGui import QPixmap, QIcon, QImageReader, QImage
from PyQt5.QtWidgets import QApplication, QGraphicsView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPicture
from PIL import Image
from PIL.ExifTags import TAGS
import hashlib
from diskcache import Cache
from PIL.ImageQt import ImageQt


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SD卡照片快速查看器")
        self.setGeometry(100, 100, 1200, 800)
        self.root_folder = os.path.dirname(os.path.abspath(__file__))
        self.current_folder = self.root_folder
        self.images = self.create_image_list()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout()
        main_widget.setLayout(layout)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.thumbnail_size = QSize(100, 100)
        self.image_list.setIconSize(self.thumbnail_size)
        self.image_list.viewport().grabGesture(Qt.PinchGesture)
        
        # 创建缓存
        self.cache = Cache(os.path.join(self.root_folder, ".thumbnails"))
        
        layout.addWidget(self.image_list)

        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout()
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget)

        open_button = QPushButton("打开文件夹")
        buttons_layout.addWidget(open_button)
        open_button.clicked.connect(self.on_open_folder_clicked)

        filter_date_layout = QGridLayout()
        buttons_layout.addLayout(filter_date_layout)
        

        filter_date_layout.addWidget(QLabel("开始日期:"), 0, 0)
        self.start_date_edit = QDateEdit()
        filter_date_layout.addWidget(self.start_date_edit, 0, 1)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDateRange(
            QDate.currentDate().addYears(-100), QDate.currentDate()
        )
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")

        filter_date_layout.addWidget(QLabel("结束日期:"), 1, 0)
        self.end_date_edit = QDateEdit()
        filter_date_layout.addWidget(self.end_date_edit, 1, 1)
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDateRange(
            QDate.currentDate().addYears(-100), QDate.currentDate()
        )
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")

        filter_date_button = QPushButton("应用日期筛选")
        buttons_layout.addWidget(filter_date_button)
        filter_date_button.clicked.connect(self.apply_date_filter)

        today_button = QPushButton("今天")
        today_button.clicked.connect(self.select_today)
        buttons_layout.addWidget(today_button)

        this_week_button = QPushButton("本周")
        this_week_button.clicked.connect(self.select_this_week)
        buttons_layout.addWidget(this_week_button)

        this_month_button = QPushButton("本月")
        this_month_button.clicked.connect(self.select_this_month)
        buttons_layout.addWidget(this_month_button)
        
        cancel_date_filter_button = QPushButton("取消日期筛选")
        buttons_layout.addWidget(cancel_date_filter_button)
        cancel_date_filter_button.clicked.connect(self.cancel_date_filter)
        
        self.image_list.itemSelectionChanged.connect(self.on_selection_changed)

        ascending_button = QPushButton("升序")
        buttons_layout.addWidget(ascending_button)
        ascending_button.clicked.connect(lambda: self.sort_images(ascending=True))

        descending_button = QPushButton("降序")
        buttons_layout.addWidget(descending_button)
        descending_button.clicked.connect(lambda: self.sort_images(ascending=False))
        
        delete_button = QPushButton("删除选中照片")
        buttons_layout.addWidget(delete_button)
        delete_button.clicked.connect(self.delete_images)

        select_all_button = QPushButton("全选")
        buttons_layout.addWidget(select_all_button)
        select_all_button.clicked.connect(self.select_all_images)

        deselect_all_button = QPushButton("取消全选")
        buttons_layout.addWidget(deselect_all_button)
        deselect_all_button.clicked.connect(self.deselect_all_images)

        buttons_layout.addStretch()

        self.statusBar()

        self.load_images()
        
        clear_cache_button = QPushButton("清理缩略图缓存")
        buttons_layout.addWidget(clear_cache_button)
        clear_cache_button.clicked.connect(self.clear_thumbnail_cache)
        
        zoom_in_button = QPushButton("+")
        buttons_layout.addWidget(zoom_in_button)
        zoom_in_button.clicked.connect(self.zoom_in)

        zoom_out_button = QPushButton("-")
        buttons_layout.addWidget(zoom_out_button)
        zoom_out_button.clicked.connect(self.zoom_out)
        
    def on_selection_changed(self):
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            item.setCheckState(Qt.Checked if item.isSelected() else Qt.Unchecked)

    def sort_images(self, ascending=True):
        self.image_list.setSortingEnabled(True)
        self.image_list.sortItems(Qt.AscendingOrder if ascending else Qt.DescendingOrder)

    def create_image_list(self):
        image_list = []
        for root, dirs, files in os.walk(self.current_folder):
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".3fr", ".ari", ".arw", ".bay", 
                                        ".cap", ".cr2", ".cr3", ".crw", ".dcr", ".dcs", ".dng", ".drf", ".eip", 
                                        ".erf", ".fff", ".gpr", ".iiq", ".k25", ".kdc", ".mdc", ".mef", ".mos", 
                                        ".mrw", ".nef", ".nrw", ".orf", ".pef", ".ptx", ".pxn", ".r3d", ".raf", 
                                        ".raw", ".rwl", ".rw2", ".rwz", ".sr2", ".srf", ".srw", ".tif", ".x3f",".HIF")):
                    image_list.append(os.path.join(root, file))
        return image_list

    def load_images(self):
        self.image_list.clear()
        for image_path in self.images:
            thumbnail_data = self.cache.get(image_path)

            if thumbnail_data is not None:
                thumbnail = QPixmap()
                thumbnail.loadFromData(QByteArray(thumbnail_data))
            else:
                thumbnail = self.generate_thumbnail(image_path)
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                thumbnail.save(buffer, "PNG")
                thumbnail_data = buffer.data()
                self.cache.set(image_path, thumbnail_data)

            icon = QIcon(thumbnail)
            item = QListWidgetItem(os.path.basename(image_path))
            item.setIcon(icon)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, image_path)  # Store the image path as item data
            self.image_list.addItem(item)

        self.image_list.itemChanged.connect(self.on_item_changed)


    def generate_thumbnail(self, image_path):
        # Open the image using PIL.Image
        image = Image.open(image_path)
        # Resize the image and keep the aspect ratio
        image.thumbnail((self.thumbnail_size.width(), self.thumbnail_size.height()), Image.ANTIALIAS)
        # Convert the PIL.Image to QImage using ImageQt
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        qimage = ImageQt(image)
        # Convert QImage to QPixmap
        pixmap = QPixmap.fromImage(qimage)
        # Return the QPixmap
        return pixmap

    def clear_thumbnail_cache(self):
        self.cache.clear()
        QMessageBox.information(self, "清理完成", "缩略图缓存已清理。")

    def zoom_in(self):
        self.set_thumbnail_size(self.thumbnail_size.width() * 1.2)

    def zoom_out(self):
        self.set_thumbnail_size(self.thumbnail_size.width() * 0.8)

    def set_thumbnail_size(self, size):
        self.thumbnail_size = QSize(size, size)
        self.image_list.setIconSize(self.thumbnail_size)
        self.load_images()

    def on_item_changed(self, item):
        item.setSelected(item.checkState() == Qt.Checked)

    def on_open_folder_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "选择一个文件夹", self.root_folder)
        if folder:
            self.current_folder = folder
            self.images = self.create_image_list()
            self.load_images()

    def apply_date_filter(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        self.images = [image for image in self.create_image_list() if self.is_image_within_date_range(image, start_date, end_date)]
        self.load_images()

    def select_today(self):
        today = datetime.date.today()
        self.start_date_edit.setDate(today)
        self.end_date_edit.setDate(today)
        self.apply_date_filter()

    def select_this_week(self):
        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        self.start_date_edit.setDate(start_of_week)
        self.end_date_edit.setDate(today)
        self.apply_date_filter()

    def select_this_month(self):
        today = datetime.date.today()
        start_of_month = today.replace(day=1)
        self.start_date_edit.setDate(start_of_month)
        self.end_date_edit.setDate(today)
        self.apply_date_filter()
        
    def cancel_date_filter(self):
        self.images = self.create_image_list()
        self.load_images()

    def is_image_within_date_range(self, image_path, start_date, end_date):
            image_date = self.get_image_date(image_path)
            return start_date <= image_date <= end_date

    def get_image_date(self, image_path):
        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    if TAGS.get(tag) == "DateTime":
                        return datetime.datetime.strptime(value, "%Y:%m:%d %H:%M:%S").date()
        except Exception as e:
            print(f"Error reading image metadata: {e}")
        return datetime.datetime.fromtimestamp(os.path.getmtime(image_path)).date()

    def delete_images(self):
        selected_items = [self.image_list.item(i) for i in range(self.image_list.count()) if self.image_list.item(i).isSelected()]

        if not selected_items:
            QMessageBox.information(self, "没有选择图片", "请选择图片进行删除.")
            return

        reply = QMessageBox.question(self, "删除图片", "你确定要删除选中的图片吗?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            for item in selected_items:
                image_path = item.data(Qt.UserRole)  # Get the image path from item data
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Error deleting image: {e}")
                    QMessageBox.critical(self, "Error", f"Error deleting image: {e}")
                self.image_list.takeItem(self.image_list.row(item))

    def select_all_images(self):
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            item.setSelected(True)

    def deselect_all_images(self):
        for index in range(self.image_list.count()):
            item = self.image_list.item(index)
            item.setSelected(False)

    def event(self, event):
        if event.type() == QEvent.Gesture:
            return self.gesture_event(event)
        return super(App, self).event(event)

    def gesture_event(self, event):
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            self.pinch_triggered(pinch)
        return True

    def pinch_triggered(self, gesture):
        changeFlags = gesture.changeFlags()
        if changeFlags & QPinchGesture.ScaleFactorChanged:
            new_size = self.thumbnail_size.width() * gesture.scaleFactor()
            self.set_thumbnail_size(new_size)

    def zoom_in(self):
        self.set_thumbnail_size(self.thumbnail_size.width() * 1.2)

    def zoom_out(self):
        self.set_thumbnail_size(self.thumbnail_size.width() * 0.8)

    def set_thumbnail_size(self, size):
        self.thumbnail_size = QSize(int(size), int(size))
        self.image_list.setIconSize(self.thumbnail_size)
        self.load_images()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())