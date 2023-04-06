import sys
import os
import glob
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QListWidget, QPushButton, QVBoxLayout, QWidget, QLabel, QGridLayout, QComboBox, QListWidgetItem
from PyQt5.QtGui import QPixmap, QImageReader
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImageReader, QIcon
from PyQt5.QtCore import QSize



class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(100, 100))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setSpacing(10)
        layout.addWidget(self.image_list)

        open_button = QPushButton("Open Folder")
        layout.addWidget(open_button)
        open_button.clicked.connect(self.open_folder)

        delete_button = QPushButton("Delete Selected Images")
        layout.addWidget(delete_button)
        delete_button.clicked.connect(self.delete_images)

        filter_layout = QGridLayout()
        layout.addLayout(filter_layout)

        filter_layout.addWidget(QLabel("Filter:"), 0, 0)

        self.filter_options = QComboBox()
        filter_layout.addWidget(self.filter_options, 0, 1)

        self.filter_options.addItem("All")
        self.filter_options.addItem("JPEG")
        self.filter_options.addItem("PNG")
        self.filter_options.addItem("GIF")

        self.filter_options.currentTextChanged.connect(self.filter_images)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select a folder")
        if folder:
            self.current_folder = folder
            self.image_paths = sorted(glob.glob(os.path.join(folder, "*")))
            self.display_images(self.image_paths)

    def display_images(self, image_paths):
        self.image_list.clear()
        for image_path in image_paths:
            pixmap = QPixmap(image_path)
            tthumbnail = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.FastTransformation)
            icon = QIcon(thumbnail)
            item = QListWidgetItem(icon, os.path.basename(image_path))
            self.image_list.addItem(item)

    def filter_images(self):
        if self.filter_options.currentText() == "All":
            self.display_images(self.image_paths)
        else:
            image_ext = f"*.{self.filter_options.currentText().lower()}"
            filtered_image_paths = sorted(glob.glob(os.path.join(            self.current_folder, image_ext)))
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


