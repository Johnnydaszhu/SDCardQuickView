import sys
import os
import glob
import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidget, QPushButton, QVBoxLayout, QWidget, QLabel, QGridLayout, QComboBox, QSplitter, QTreeView, QFileSystemModel, QSizePolicy, QDateEdit
from PyQt5.QtGui import QPixmap, QIcon, QImageReader
from PyQt5.QtCore import Qt, QSize, QDir, QUrl, QMimeData, QModelIndex, QThread, pyqtSignal
from functools import lru_cache
from PIL import Image
from PIL.ExifTags import TAGS
from PyQt5.QtWidgets import QListWidgetItem

import concurrent.futures


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


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSpacing(10)
        self.image_list.setSelectionMode(QListWidget.ExtendedSelection)
        splitter.addWidget(self.image_list)

        self.image_list.itemClicked.connect(self.show_exif_info)
        self.image_list.itemDoubleClicked.connect(self.open_image)

        self.tree_view = QTreeView()
        self.tree_view.setAcceptDrops(True)
        self.tree_view.viewport().setAcceptDrops(True)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setDropIndicatorShown(True)
        self.tree_view.setDragDropMode(QTreeView.DropOnly)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDragDropMode(QTreeView.DropOnly)
        self.tree_view.dragEnterEvent = self.dragEnterEvent
        self.tree_view.dropEvent = self.dropEvent
        splitter.addWidget(self.tree_view)

        self.image_preview = QLabel()
        self.image_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_preview.setAlignment(Qt.AlignCenter)
        splitter.addWidget(self.image_preview)

        self.file_system_model = QFileSystemModel()
        self.tree_view.setModel(self.file_system_model)

        self.image_paths = []

        self.tree_view.setRootIndex(self.file_system_model.index(""))
        splitter.addWidget(self.tree_view)

        buttons_layout = QVBoxLayout()
        layout.addLayout(buttons_layout)

        show_all_button = QPushButton("Show All Images")
        buttons_layout.addWidget(show_all_button)
        show_all_button.clicked.connect(self.show_all_images)

        open_button = QPushButton("Open Folder")
        buttons_layout.addWidget(open_button)
        open_button.clicked.connect(self.on_open_folder_clicked)

        generate_preview_button = QPushButton("Generate Preview")
        buttons_layout.addWidget(generate_preview_button)
        generate_preview_button.clicked.connect(self.generate_preview)

        delete_button = QPushButton("Delete Selected Images")
        buttons_layout.addWidget(delete_button)
        delete_button.clicked.connect(self.delete_images)

        filter_layout = QGridLayout()
        buttons_layout.addLayout(filter_layout)

        filter_layout.addWidget(QLabel("Filter:"), 0, 0)

        self.filter_options = QComboBox()
        filter_layout.addWidget(self.filter_options, 0, 1)

        self.filter_options.addItem("All")
        self.filter_options.addItem("JPEG")
        self.filter_options.addItem("PNG")
        self.filter_options.addItem("GIF")

        self.filter_options.currentTextChanged.connect(self.filter_images)

        self.tree_view.clicked.connect(self.tree_item_clicked)

        filter_date_layout = QGridLayout()
        buttons_layout.addLayout(filter_date_layout)

       
        filter_date_layout.addWidget(QLabel("Filter Date:"), 0, 0)

        self.date_edit = QDateEdit()
        filter_date_layout.addWidget(self.date_edit, 0, 1)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDateRange(datetime.date.min, datetime.date.today())
        self.date_edit.setDate(datetime.date.today())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.dateChanged.connect(self.filter_date)

        today_button = QPushButton("Today")
        buttons_layout.addWidget(today_button)
        today_button.clicked.connect(self.filter_today)

        this_week_button = QPushButton("This Week")
        buttons_layout.addWidget(this_week_button)
        this_week_button.clicked.connect(self.filter_this_week)


    def open_image(self, item):
        image_path = os.path.join(self.current_folder, item.text())
        pixmap = QPixmap(image_path)
        self.image_preview.setPixmap(pixmap.scaled(self.image_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def add_thumbnail_to_list(self, image_path, pixmap):
        item = QListWidgetItem(QIcon(pixmap), os.path.basename(image_path))
        self.image_list.addItem(item)

    def show_exif_info(self, item):
        image_path = os.path.join(self.current_folder, item.text())
        exif_data = self.get_exif_data(image_path)
        if exif_data:
            exif_info = "\n".join(f"{key}: {value}" for key, value in exif_data.items())
            print(exif_info)  # Print EXIF data to the console, you can change this to display it somewhere else if you prefer
        else:
            print("No EXIF data found")

    def get_exif_data(self, image_path):
        try:
            image = Image.open(image_path)
            exif_data = image._getexif()
            if exif_data:
                return {TAGS.get(tag): value for tag, value in exif_data.items() if tag in TAGS}
        except Exception as e:
            print(f"Error getting EXIF data: {e}")
        return None

    def filter_date(self):
        selected_date = self.date_edit.date().toPyDate()
        filtered_image_paths = [path for path in self.image_paths if self.get_image_creation_date(path) == selected_date]
        self.display_images(filtered_image_paths)

    def filter_today(self):
        self.date_edit.setDate(datetime.date.today())
        self.filter_date()

    def filter_this_week(self):
        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        filtered_image_paths = [path for path in self.image_paths if start_of_week <= self.get_image_creation_date(path) <= today]
        self.display_images(filtered_image_paths)

    def get_image_creation_date(self, image_path):
        exif_data = self.get_exif_data(image_path)
        if exif_data and "DateTimeOriginal" in exif_data:
            try:
                date_string = exif_data["DateTimeOriginal"]
                return datetime.datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S").date()
            except ValueError:
                pass
        return datetime.date.fromtimestamp(os.path.getmtime(image_path))


    def show_all_images(self):
        self.display_images(self.image_paths)


    def open_folder(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Select a folder", "", QFileDialog.ShowDirsOnly)
        if folder:
            self.current_folder = folder
            self.image_paths = sorted(self.get_image_files(folder))
            self.file_system_model.setRootPath(folder)
            self.tree_view.setRootIndex(self.file_system_model.index(folder))
            self.generate_preview()

            if hasattr(self, 'loader'):
                self.loader.stop()
                self.loader.wait()

            self.loader = ImageLoader(self.image_paths)
            self.loader.image_loaded.connect(self.add_thumbnail_to_list)
            self.loader.start()


            
    def on_open_folder_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder", "", QFileDialog.ShowDirsOnly)
        if folder:
            self.open_folder(folder)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super(App, self).dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            folder = url.toLocalFile()
            self.open_folder(folder)
            event.acceptProposedAction()
        else:
            super(App, self).dropEvent(event)

    def generate_preview(self):
        if not hasattr(self, 'image_paths'):
            return
        self.display_images(self.image_paths)

    def get_image_files(self, folder):
        image_files = []
        extensions = ['jpg', 'jpeg', 'png', 'gif']
        for root, _, files in os.walk(folder):
            for file in files:
                if file.split('.')[-1].lower() in extensions:
                    image_files.append(os.path.join(root, file))
        return image_files

    def display_images(self, image_paths):
        self.image_list.clear()
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.load_thumbnail, image_path) for image_path in image_paths]
            for future in concurrent.futures.as_completed(futures):
                item, icon = future.result()
                self.image_list.addItem(item)
                item.setIcon(icon)

    @lru_cache(maxsize=128)
    def load_thumbnail(self, image_path):
        pixmap = QPixmap(image_path)
        thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(thumbnail)
        item = QListWidgetItem(icon, os.path.basename(image_path))
        return item, icon
    
    def load_thumbnail(self, image_path):
        pixmap = QPixmap(image_path)
        thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon = QIcon(thumbnail)
        item = QListWidgetItem(icon, os.path.basename(image_path))
        return item, icon

    def tree_item_clicked(self, index):
        path = self.file_system_model.filePath(index)
        if os.path.isdir(path):
            self.image_paths = sorted(self.get_image_files(path))
            self.display_images(self.image_paths)



    def filter_images(self):
        if self.filter_options.currentText() == "All":
            self.display_images(self.image_paths)
        else:
            image_ext = f"*.{self.filter_options.currentText().lower()}"
            filtered_image_paths = [path for path in self.image_paths if path.lower().endswith(image_ext.lower())]
            self.display_images(filtered_image_paths)

    def delete_images(self):
        selected_items = self.image_list.selectedItems()
        for item in selected_items:
            image_path = os.path.join(self.current_folder, item.text())
            os.remove(image_path)
            self.image_list.takeItem(self.image_list.row(item))

if __name__ == "__main__":
    app_instance = QApplication(sys.argv)
    main_app = App()
    main_app.setAcceptDrops(True)  # Enable drag and drop for the entire app
    main_app.show()
    sys.exit(app_instance.exec_())
