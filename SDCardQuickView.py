import sys
import os
import glob
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidget, QPushButton, QVBoxLayout, QWidget, QLabel, QGridLayout, QComboBox, QListWidgetItem, QSplitter, QTreeView, QFileSystemModel,QProgressBar
from PyQt5.QtGui import QPixmap, QIcon, QImageReader
from PyQt5.QtGui import QPixmap, QIcon, QImageReader
from PyQt5.QtCore import Qt, QSize, QDir

class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.tree_view = QTreeView()
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())
        self.tree_view.setModel(self.file_system_model)
        splitter.addWidget(self.tree_view)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSpacing(10)
        splitter.addWidget(self.image_list)

        buttons_layout = QVBoxLayout()
        layout.addLayout(buttons_layout)

        open_button = QPushButton("Open Folder")
        buttons_layout.addWidget(open_button)
        open_button.clicked.connect(self.open_folder)

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

    def open_folder(self, folder=None):
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Select a folder")
        if folder:
            self.current_folder = folder
            self.image_paths = sorted(self.get_image_files(folder))

    def generate_preview(self):
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
        self.progress_bar.setRange(0, len(image_paths))
        self.progress_bar.setValue(0)
        for idx, image_path in enumerate(image_paths):
            pixmap = QPixmap(image_path)
            thumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon = QIcon(thumbnail)
            item = QListWidgetItem(icon, os.path.basename(image_path))
            self.image_list.addItem(item)
            self.progress_bar.setValue(idx + 1)

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
    app = QApplication(sys.argv)
    main_app = App()
    main_app.show()
    sys.exit(app.exec_())

