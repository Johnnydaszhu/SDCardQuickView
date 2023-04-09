import sys
import io
import os
import datetime
import cProfile
import pstats
from functools import lru_cache
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QSizePolicy,
    QListWidget,
    QPushButton,
    QGridLayout,
    QComboBox,
    QDateEdit,
    QFileSystemModel,
    QTreeView,
    QListWidgetItem,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QModelIndex, QDate
from PyQt5.QtGui import QPixmap, QIcon, QImage, QColor
from PIL.ImageQt import ImageQt

import concurrent.futures
from PIL import Image
from PIL.ExifTags import TAGS


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
        layout.addWidget(self.image_list)

        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout()
        buttons_widget.setLayout(buttons_layout)
        layout.addWidget(buttons_widget)

        open_button = QPushButton("Open Folder")
        buttons_layout.addWidget(open_button)
        open_button.clicked.connect(self.on_open_folder_clicked)

        filter_date_layout = QGridLayout()
        buttons_layout.addLayout(filter_date_layout)

        filter_date_layout.addWidget(QLabel("Start Date:"), 0, 0)
        self.start_date_edit = QDateEdit()
        filter_date_layout.addWidget(self.start_date_edit, 0, 1)
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDateRange(
            QDate.currentDate().addYears(-100), QDate.currentDate()
        )
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-1))
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")

        filter_date_layout.addWidget(QLabel("End Date:"), 1, 0)
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
            pixmap = QPixmap()
            pixmap.load(image_path)
            icon = QIcon(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
            item = QListWidgetItem(os.path.basename(image_path))
            item.setIcon(icon)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, image_path)  # Store the image path as item data
            self.image_list.addItem(item)

        self.image_list.itemChanged.connect(self.on_item_changed)

    def on_item_changed(self, item):
        item.setSelected(item.checkState() == Qt.Checked)
    
    def on_open_folder_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder", self.root_folder)
        if folder:
            self.current_folder = folder
            self.images = self.create_image_list()
            self.load_images()

    def apply_date_filter(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        self.images = [image for image in self.create_image_list() if self.is_image_within_date_range(image, start_date, end_date)]
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
            QMessageBox.information(self, "No images selected", "Please select images to delete.")
            return

        reply = QMessageBox.question(self, "Delete Images", "Are you sure you want to delete the selected images?",
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

