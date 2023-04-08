import sys
import io
import os
import datetime
import cProfile
import pstats
from functools import lru_cache
from PyQt5.QtWidgets import QDockWidget

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
    QDockWidget
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QModelIndex, QDate
from PyQt5.QtGui import QPixmap, QIcon, QImage, QColor
from PIL.ImageQt import ImageQt

import concurrent.futures
from PIL import Image
from PIL.ExifTags import TAGS

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif",".HEIC",".ARW",".RAW",".HIF",".DNG",".JPG")

class CustomTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.parent().parent().parent().on_open_folder_clicked()
        super().mousePressEvent(event)

class ImageLoader(QThread):
    image_loaded = pyqtSignal(str, QPixmap)

    def __init__(self, image_paths):
        super().__init__()
        self.image_paths = image_paths

    def run(self):
        for image_path in self.image_paths:
            pixmap = QPixmap(image_path)
            self.image_loaded.emit(image_path, pixmap)

    def stop(self):
        self.terminate()


    def set_properties(self, properties):
        self.property_table.setRowCount(len(properties))
        for row, (name, value) in enumerate(properties):
            name_item = QTableWidgetItem(name)
            value_item = QTableWidgetItem(str(value))
            self.property_table.setItem(row, 0, name_item)
            self.property_table.setItem(row, 1, value_item)



class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 1200, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # 删除空白区域

        self.file_system_model = QFileSystemModel()

        self.image_preview_label = QLabel()
        # splitter.addWidget(self.image_preview_label)

        self.tree_view = CustomTreeView(self)
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setRootIndex(self.file_system_model.index(""))
        splitter.addWidget(self.tree_view)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(200, 200))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSelectionMode(QListWidget.ExtendedSelection)
        splitter.addWidget(self.image_list)

        buttons_widget = QWidget()
        splitter.addWidget(buttons_widget)
        buttons_layout = QVBoxLayout(buttons_widget)

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

        self.file_list_widget = QListWidget()
        layout.addWidget(self.file_list_widget)

        filter_date_layout.addWidget(QLabel("End Date:"), 1, 0)
        self.end_date_edit = QDateEdit()
        filter_date_layout.addWidget(self.end_date_edit, 1, 1)
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDateRange(
            QDate.currentDate().addYears(-100), QDate.currentDate()
        )
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")

        filter_date_button = QPushButton("Apply Date Filter")
        buttons_layout.addWidget(filter_date_button)
        filter_date_button.clicked.connect(self.apply_date_filter)

        generate_preview_button = QPushButton("Generate Preview")
        buttons_layout.addWidget(generate_preview_button)
        generate_preview_button.clicked.connect(self.generate_preview)

        delete_button = QPushButton("Delete Selected Images")
        buttons_layout.addWidget(delete_button)
        delete_button.clicked.connect(self.delete_images)

        select_all_button = QPushButton("Select All")
        buttons_layout.addWidget(select_all_button)
        select_all_button.clicked.connect(self.select_all_images)

        deselect_all_button = QPushButton("Deselect All")
        buttons_layout.addWidget(deselect_all_button)
        deselect_all_button.clicked.connect(self.deselect_all_images)

        self.tree_view.clicked.connect(self.tree_item_clicked)
        self.tree_view.clicked.connect(self.on_open_folder_clicked)

        self.image_list.itemClicked.connect(self.open_image)
        self.image_list.itemDoubleClicked.connect(self.open_image)
        self.image_list.setContextMenuPolicy(Qt.CustomContextMenu)

        self.setMouseTracking(True)
        self.mousePressEvent = self.on_mouse_press_event



    def on_mouse_press_event(self, event):
        print(f"Mouse clicked on {event.pos()} in widget {self.sender()}")


    def mousePressEvent(self, event):
        widget = self.childAt(event.pos())
        if widget is not None:
            print(f"Mouse clicked on {event.pos()} in widget {widget.objectName()}")
        else:
            print(f"Mouse clicked on {event.pos()} in empty area")



    def tree_item_clicked(self, index):
        path = self.file_system_model.filePath(index)
        if os.path.isdir(path):
            self.load_images(path)

    def open_image(self, item):
        image_path = os.path.join(self.current_folder, item.text())
        image_preview = QPixmap(image_path)
        if image_preview.width() > self.image_preview_label.width() or image_preview.height() > self.image_preview_label.height():
            image_preview = image_preview.scaled(self.image_preview_label.width(), self.image_preview_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_preview_label.setPixmap(image_preview)

        # Show EXIF info window
        properties = []
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            if exif_data:
                for tag_id in exif_data:
                    tag_name = TAGS.get(tag_id, tag_id)
                    tag_value = exif_data.get(tag_id)
                    if isinstance(tag_value, bytes):
                        tag_value = tag_value.decode("utf-8", errors="replace")
                    properties.append((tag_name, tag_value))

        if properties:
            exif_window = ExifInfoWindow(self)
            exif_window.set_properties(properties)
            exif_window.show()

    def open_exif_info_window(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return

        if len(selected_items) == 1:
            image_path = os.path.join(self.current_folder, selected_items[0].text())
            with Image.open(image_path) as img:
                exif_data = img.getexif()
            if exif_data:
                properties = []
                for tag_id in exif_data:
                    tag_name = TAGS.get(tag_id, tag_id)
                    tag_value = exif_data.get(tag_id)
                    if isinstance(tag_value, bytes):
                        tag_value = tag_value.decode("utf-8", errors="replace")
                    properties.append((tag_name, tag_value))
                self.exif_dock_widget.set_properties(properties)
                self.exif_dock_widget.show()
            else:
                QMessageBox.warning(
                    self, "No EXIF Information", "No EXIF data found for this image."
                )
        else:
            QMessageBox.warning(
                self, "Multiple Images Selected", "Please select only one image."
            )

        # 获取缩略图
    def get_thumbnail(file_path, size=(128, 128)):
        with Image.open(file_path) as image:
            image.thumbnail(size)
            return image

    # 将图像转换为QPixmap
    def get_pixmap(image):
        image_data = image.tobytes()
        qimage = QtGui.QImage(image_data, image.size[0], image.size[1], QtGui.QImage.Format_RGB888)
        pixmap = QtGui.QPixmap.fromImage(qimage)
        return pixmap

    # 设置列表项目的缩略图
    def set_thumbnail(item, file_path):
        image = get_thumbnail(file_path)
        pixmap = get_pixmap(image)
        item.setIcon(QtGui.QIcon(pixmap))
    
    def apply_filter(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        selected_items = self.image_list.selectedItems()

        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            image_path = os.path.join(self.current_folder, item.text())
            creation_time = datetime.datetime.fromtimestamp(
                os.path.getctime(image_path)
            ).date()
            if start_date <= creation_time <= end_date:
                item.setHidden(False)
            else:
                item.setHidden(True)
    

    def open_exif_info_window(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return

        if len(selected_items) == 1:
            image_path = os.path.join(self.current_folder, selected_items[0].text())
            with Image.open(image_path) as img:
                exif_data = img.getexif()
            if exif_data:
                exif_str = ""
                for tag_id in exif_data:
                    tag_name = TAGS.get(tag_id, tag_id)
                    tag_value = exif_data.get(tag_id)
                    if isinstance(tag_value, bytes):
                        tag_value = tag_value.decode("utf-8", errors="replace")
                    exif_str += f"{tag_name}: {tag_value}\n"
                QMessageBox.information(self, "EXIF Information", exif_str)
            else:
                QMessageBox.warning(
                    self, "No EXIF Information", "No EXIF data found for this image."
                )
        else:
            exif_str = ""
            for item in selected_items:
                image_path = os.path.join(self.current_folder, item.text())
                with Image.open(image_path) as img:
                    exif_data = img.getexif()
                if exif_data:
                    exif_str += f"EXIF Information for {item.text()}:\n"
                    for tag_id in exif_data:
                        tag_name = TAGS.get(tag_id, tag_id)
                        tag_value = exif_data.get(tag_id)
                        if isinstance(tag_value, bytes):
                            tag_value = tag_value.decode("utf-8", errors="replace")
                        exif_str += f"{tag_name}: {tag_value}\n"
                else:
                    exif_str += f"No EXIF data found for {item.text()}.\n"
                exif_str += "\n"
            exif_window = ExifInfoWindow(exif_str)
            exif_window.show()

    def generate_preview_worker(self, image_path):
        preview_size = QSize(200, 200)
        image = Image.open(image_path)
        image.thumbnail(preview_size)
        preview = QPixmap.fromImage(ImageQt(image))
        return image_path, preview


    def set_properties(self, properties):
        self.property_table.setRowCount(len(properties))
        for row, (name, value) in enumerate(properties):
            name_item = QTableWidgetItem(name)
            value_item = QTableWidgetItem(str(value))
            self.property_table.setItem(row, 0, name_item)
            self.property_table.setItem(row, 1, value_item)

    def clear_properties(self):
        self.property_table.setRowCount(0)


    def apply_date_filter(self):
        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()
        selected_items = self.image_list.selectedItems()

        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            image_path = os.path.join(self.current_folder, item.text())
            creation_time = datetime.datetime.fromtimestamp(
                os.path.getctime(image_path)
            ).date()
            if start_date <= creation_time <= end_date:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def on_open_folder_clicked(self):
        # Open a file dialog to select a folder
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")


        if folder_path:
            # Clear the previous items in the list
            self.file_list_widget.clear()

            # Add the files in the folder to the list
            for file_name in os.listdir(folder_path):
                if file_name.endswith(IMAGE_EXTENSIONS):
                    file_path = os.path.join(folder_path, file_name)
                    item = QListWidgetItem(file_name)
                    item.setToolTip(file_path)
                    self.file_list_widget.addItem(item)



    def select_all_images(self):
        self.image_list.selectAll()

    def deselect_all_images(self):
        self.image_list.clearSelection()

    def delete_images(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            reply = QMessageBox.question(
                self,
                "Delete Images",
                "Are you sure you want to delete the selected images?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default value
            )

            if reply == QMessageBox.Yes:
                for item in selected_items:
                    image_path = os.path.join(self.current_folder, item.text())
                    os.remove(image_path)
                    self.image_list.takeItem(self.image_list.row(item))


    def load_images(self, folder):
        self.image_list.clear()
        image_files = [
            f
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower()
            in {".jpg", ".jpeg", ".png", ".gif",".HEIC",".ARW",".RAW",".HIF",".DNG",".JPG"}
        ]
        for image_file in image_files:
            item = QListWidgetItem(image_file)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            set_thumbnail(item, os.path.join(folder, image_file))  # 设置缩略图
            self.image_list.addItem(item)

    def generate_preview(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for item in selected_items:
                    image_path = os.path.join(self.current_folder, item.text())
                    future = executor.submit(self.generate_preview_worker, image_path)
                    futures.append(future)

                for future in concurrent.futures.as_completed(futures):
                    image_path, preview = future.result()
                    for i in range(self.image_list.count()):
                        item = self.image_list.item(i)
                        if item.text() == os.path.basename(image_path):
                            item.setIcon(QIcon(preview))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())

