#!/usr/bin/env python3
import sys
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QListWidget, QLabel, QPushButton,
                             QLineEdit, QTextEdit, QInputDialog, QMessageBox,
                             QListWidgetItem, QStyle, QSplitter, QProgressDialog,
                             QComboBox, QDialog, QGridLayout, QSlider)
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import (QFontDatabase, QFont, QColor, QPalette,
                         QTextDocument, QTextCursor, QTextCharFormat,
                         QTextBlockFormat, QBrush)

# --- Configuration ---
ROOT_PATH = os.path.normpath("/home/prakriti/Documents/fontcollection")
FONT_EXTENSIONS = ('.ttf', '.otf', '.ttc', '.woff', '.woff2')
SYSTEM_FONT_PATH = "/usr/share/fonts"

class EditTextDialog(QDialog):
    def __init__(self, current_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Heading Text")
        self.resize(400, 200)
        self.new_text = current_text
        self.is_reset = False

        layout = QVBoxLayout(self)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(current_text)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()

        btn_ok = QPushButton("Apply")
        btn_ok.clicked.connect(self.accept)

        btn_reset = QPushButton("Reset to Default")
        btn_reset.setStyleSheet("color: #aa3333;")
        btn_reset.clicked.connect(self.reset_text)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def reset_text(self):
        self.is_reset = True
        self.accept()

    def get_text(self):
        if self.is_reset:
            return None
        return self.text_edit.toPlainText()

class FontViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.root_path = ROOT_PATH
        self.current_path = self.root_path
        self.selected_font_path = None
        self.search_mode = False
        self.current_font_family = None

        # --- State Variables ---
        self.default_heading_text = "The quick brown fox jumps over the lazy dog."
        self.heading_text = self.default_heading_text
        self.is_caps = False
        self.zoom_level = 100

        os.makedirs(self.root_path, exist_ok=True)

        self.init_ui()

        # Load Default Directory
        self.load_directory(self.current_path)

        # --- "OPEN WITH" FEATURE ---
        # Check if a file path was passed as an argument
        if len(sys.argv) > 1:
            file_arg = sys.argv[1]
            if os.path.exists(file_arg) and file_arg.lower().endswith(FONT_EXTENSIONS):
                # Load the file immediately
                self.load_font_file(file_arg)

    def init_ui(self):
        self.setWindowTitle("Linux Font Viewer")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- TOP BAR ---
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_back = QPushButton("cd ..")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.clicked.connect(self.go_back)

        self.btn_home = QPushButton("cd ~")
        self.btn_home.setIcon(self.style().standardIcon(QStyle.SP_DirHomeIcon))
        self.btn_home.clicked.connect(self.go_home)

        self.address_bar = QLineEdit()
        self.address_bar.setReadOnly(True)
        self.address_bar.setText(self.current_path)

        self.btn_install = QPushButton("Install Font")
        self.btn_install.setEnabled(False)
        self.btn_install.clicked.connect(self.install_font)

        top_bar_layout.addWidget(self.btn_back)
        top_bar_layout.addWidget(self.btn_home)
        top_bar_layout.addWidget(self.address_bar)
        top_bar_layout.addWidget(self.btn_install)

        # --- CONTENT AREA ---
        content_splitter = QSplitter(Qt.Horizontal)

        # 1. Sidebar Container
        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(5)

        # Style Selector
        style_container = QWidget()
        style_container.setFixedHeight(40)
        style_layout = QHBoxLayout(style_container)
        style_layout.setContentsMargins(5, 0, 5, 0)
        style_label = QLabel("Style:")
        style_label.setStyleSheet("color: #888; font-weight: bold;")
        self.style_combo = QComboBox()
        self.style_combo.addItem("No Font Selected")
        self.style_combo.setEnabled(False)
        self.style_combo.currentTextChanged.connect(self.on_style_changed)
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)

        # Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search fonts...")
        self.search_bar.setFixedHeight(30)
        self.search_bar.textChanged.connect(self.handle_search)

        # File List
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_item_clicked)
        self.file_list.setMinimumWidth(200)

        sidebar_layout.addWidget(style_container)
        sidebar_layout.addWidget(self.search_bar)
        sidebar_layout.addWidget(self.file_list)

        # 2. Canvas Area
        right_container = QWidget()
        right_layout = QGridLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Main Canvas
        self.canvas = QTextEdit()
        self.canvas.setReadOnly(True)
        self.canvas.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: none;
                padding: 50px;
            }
        """)
        right_layout.addWidget(self.canvas, 0, 0, 2, 2)

        # Overlay Buttons (Top Left)
        overlay_container = QWidget()
        overlay_layout = QHBoxLayout(overlay_container)
        overlay_layout.setContentsMargins(10, 10, 0, 0) # Top, Left

        btn_caps = QPushButton("Toggle Caps")
        btn_caps.setStyleSheet("padding: 5px; background-color: #444; color: white;")
        btn_caps.clicked.connect(self.toggle_caps)

        btn_edit = QPushButton("Edit Text")
        btn_edit.setStyleSheet("padding: 5px; background-color: #444; color: white;")
        btn_edit.clicked.connect(self.edit_text)

        overlay_layout.addWidget(btn_caps)
        overlay_layout.addWidget(btn_edit)

        right_layout.addWidget(overlay_container, 0, 0, 1, 1, Qt.AlignTop | Qt.AlignLeft)

        # Zoom Slider (Bottom)
        zoom_container = QWidget()
        zoom_container.setFixedHeight(50)
        zoom_container.setStyleSheet("background-color: #333; border-top: 1px solid #444;")
        zoom_layout = QHBoxLayout(zoom_container)
        zoom_layout.setContentsMargins(50, 5, 50, 5)

        zoom_label = QLabel("Heading Zoom:")
        zoom_label.setStyleSheet("color: white;")

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(200)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.update_zoom)

        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)

        right_layout.addWidget(zoom_container, 1, 0, 1, 2)

        content_splitter.addWidget(sidebar_container)
        content_splitter.addWidget(right_container)
        content_splitter.setStretchFactor(1, 4)

        main_layout.addWidget(top_bar)
        main_layout.addWidget(content_splitter)

        self.apply_dark_theme()

    def apply_dark_theme(self):
        app = QApplication.instance()
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)

    def check_install_status(self):
        if not self.selected_font_path:
            self.btn_install.setEnabled(False)
            self.btn_install.setText("Install Font")
            return

        filename = os.path.basename(self.selected_font_path)
        dest_path = os.path.join(SYSTEM_FONT_PATH, filename)

        if os.path.exists(dest_path):
            self.btn_install.setEnabled(False)
            self.btn_install.setText("Already Installed")
        else:
            self.btn_install.setEnabled(True)
            self.btn_install.setText("Install Font")

    def load_directory(self, path):
        requested_path = os.path.normpath(path)

        if not requested_path.startswith(self.root_path):
            # We only enforce this for manual navigation.
            # Opening via sys.argv bypasses this.
            QMessageBox.warning(self, "Access Denied", "Cannot navigate outside the font collection.")
            return

        self.current_path = requested_path
        self.address_bar.setText(self.current_path)
        self.file_list.clear()
        self.search_mode = False
        self.btn_install.setEnabled(False)
        self.btn_install.setText("Install Font")

        self.style_combo.blockSignals(True)
        self.style_combo.clear()
        self.style_combo.addItem("No Font Selected")
        self.style_combo.setEnabled(False)
        self.style_combo.blockSignals(False)

        self.current_font_family = None

        try:
            items = os.listdir(self.current_path)
            folders = []
            font_files = []

            for item in items:
                item_path = os.path.join(self.current_path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                elif item.lower().endswith(FONT_EXTENSIONS):
                    font_files.append(item)

            folders.sort(key=str.lower)
            font_files.sort(key=str.lower)

            for item in folders:
                list_item = QListWidgetItem(item)
                list_item.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
                self.file_list.addItem(list_item)

            for item in font_files:
                list_item = QListWidgetItem(item)
                list_item.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
                self.file_list.addItem(list_item)

        except PermissionError:
            err_item = QListWidgetItem("[Permission Denied]")
            err_item.setForeground(QColor("red"))
            self.file_list.addItem(err_item)

        self.canvas.clear()

    def handle_search(self, text):
        if not text:
            self.load_directory(self.current_path)
            return

        self.search_mode = True
        self.file_list.clear()
        self.address_bar.setText(f"Searching: {text}")

        for root, dirs, files in os.walk(self.root_path):
            for file in files:
                if text.lower() in file.lower() and file.lower().endswith(FONT_EXTENSIONS):
                    rel_path = os.path.relpath(os.path.join(root, file), self.root_path)
                    list_item = QListWidgetItem(file)
                    list_item.setToolTip(rel_path)
                    list_item.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
                    self.file_list.addItem(list_item)

    def on_style_changed(self, style_name):
        if self.current_font_family and style_name != "No Font Selected":
            self.display_font(self.current_font_family, style_name)

    def on_item_clicked(self, item):
        text = item.text()

        if self.search_mode:
            full_path = os.path.join(self.root_path, item.toolTip())
            if os.path.exists(full_path):
                self.load_font_file(full_path)
            return

        item_path = os.path.join(self.current_path, text)

        if os.path.isdir(item_path):
            self.load_directory(item_path)
        elif text.lower().endswith(FONT_EXTENSIONS):
            if os.path.exists(item_path):
                self.load_font_file(item_path)

    def load_font_file(self, path):
        try:
            # If the file is external (via sys.argv), update the address bar for clarity
            if not path.startswith(self.root_path):
                self.address_bar.setText(f"Viewing: {path}")

            font_db = QFontDatabase()
            font_id = font_db.addApplicationFont(path)

            if font_id == -1:
                QMessageBox.warning(self, "Error", "Could not load font file.")
                return

            families = font_db.applicationFontFamilies(font_id)
            if not families:
                return

            self.current_font_family = families[0]
            self.selected_font_path = path

            self.check_install_status()

            try:
                styles = font_db.styles(self.current_font_family)
            except:
                styles = ["Regular"]

            if not styles:
                styles = ["Regular"]

            self.style_combo.blockSignals(True)
            self.style_combo.clear()
            self.style_combo.addItems(styles)
            self.style_combo.setEnabled(True)
            self.style_combo.blockSignals(False)

            self.display_font(self.current_font_family, styles[0])

        except Exception as e:
            print(f"Error loading font: {e}")

    def update_zoom(self):
        self.zoom_level = self.zoom_slider.value()
        if self.current_font_family:
            style = self.style_combo.currentText()
            if style != "No Font Selected":
                self.display_font(self.current_font_family, style)

    def toggle_caps(self):
        self.is_caps = not self.is_caps
        if self.current_font_family:
            style = self.style_combo.currentText()
            if style != "No Font Selected":
                self.display_font(self.current_font_family, style)

    def edit_text(self):
        dialog = EditTextDialog(self.heading_text, self)
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_text()
            if result is None:
                self.heading_text = self.default_heading_text
            else:
                self.heading_text = result

            if self.current_font_family:
                style = self.style_combo.currentText()
                if style != "No Font Selected":
                    self.display_font(self.current_font_family, style)

    def display_font(self, family, style):
        try:
            font_db = QFontDatabase()

            display_heading = self.heading_text
            if self.is_caps:
                display_heading = display_heading.upper()

            body = (
                "The quick brown fox jumps over the lazy dog, not because he is in a hurry, but because the quiet afternoon makes him restless. The sun hangs low in the sky, warming the grass, and the fox feels a sudden urge to prove that his legs are still strong and swift. The dog barely opens one eye, letting out a slow yawn, unimpressed by the fox’s display."
                "After landing softly on the other side, the fox pauses and looks back. He notices that the dog is old, tired, and comfortable in his laziness. For a moment, the fox feels a strange mix of pride and sympathy. Speed and cleverness have always been his strengths, but watching the dog rest so peacefully makes him wonder if constant movement is truly necessary."
                "The dog finally lifts his head and speaks in a calm voice, telling the fox that there is wisdom in resting and joy in being content. The fox listens carefully, realizing that life is not only about jumping higher or running faster. Sometimes, it is also about knowing when to slow down."
                "As evening approaches, the fox walks away more thoughtfully than before. The dog closes his eyes again, smiling slightly. In that quiet field, both animals learn something important balance between action and rest is what makes life complete."
            )
            ending = "--------------~12345!@#$)000(%^&*67890~--------------"

            doc = QTextDocument()
            cursor = QTextCursor(doc)

            block_fmt_normal = QTextBlockFormat()
            block_fmt_normal.setBottomMargin(5)
            block_fmt_normal.setTopMargin(0)

            block_fmt_large_gap = QTextBlockFormat()
            block_fmt_large_gap.setBottomMargin(15)
            block_fmt_large_gap.setTopMargin(10)

            # 1. Style Label
            cursor.insertBlock(block_fmt_normal)
            style_lbl_fmt = QTextCharFormat()
            style_lbl_fmt.setForeground(QBrush(QColor("gray")))
            style_lbl_fmt.setFont(QFont("sans-serif", 10))
            cursor.insertText(f"STYLE: {style.upper()}\n", style_lbl_fmt)

            # 2. Heading
            base_size = 48
            final_heading_size = int(base_size * (self.zoom_level / 100.0))
            head_font = font_db.font(family, style, final_heading_size)
            head_fmt = QTextCharFormat()
            head_fmt.setFont(head_font)
            head_fmt.setForeground(QBrush(QColor("white")))

            cursor.insertBlock(block_fmt_large_gap)
            cursor.insertText(display_heading + "\n", head_fmt)

            # 3. Body (Fixed 13px)
            body_font = font_db.font(family, style, 13)
            body_fmt = QTextCharFormat()
            body_fmt.setFont(body_font)
            body_fmt.setForeground(QBrush(QColor("white")))

            cursor.insertBlock(block_fmt_large_gap)
            cursor.insertText(body + "\n\n", body_fmt)

            # 4. Ending (Fixed 13px)
            end_font = font_db.font(family, style, 13)
            end_fmt = QTextCharFormat()
            end_fmt.setFont(end_font)
            end_fmt.setForeground(QBrush(QColor("#aaaaaa")))

            end_block_fmt = QTextBlockFormat()
            end_block_fmt.setAlignment(Qt.AlignHCenter)
            end_block_fmt.setTopMargin(10)
            end_block_fmt.setBottomMargin(20)

            cursor.insertBlock(end_block_fmt)
            cursor.insertText(ending, end_fmt)

            self.canvas.setDocument(doc)

        except Exception as e:
            print(f"Error rendering font: {e}")
            self.canvas.setHtml(f"<div style='color:white;'>Error rendering: {str(e)}</div>")

    def go_back(self):
        parent = os.path.dirname(self.current_path)
        if parent.startswith(self.root_path) or os.path.normpath(parent) == os.path.dirname(self.root_path):
             if os.path.exists(parent):
                 self.load_directory(parent)

    def go_home(self):
        self.load_directory(self.root_path)

    def install_font(self):
        if not self.selected_font_path:
            return

        password, ok = QInputDialog.getText(self, "Install Font", "Enter sudo password:", QLineEdit.Password)

        if ok and password:
            progress = QProgressDialog("Installing font...", None, 0, 0, self)
            progress.setWindowTitle("Processing")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            QApplication.processEvents()

            try:
                filename = os.path.basename(self.selected_font_path)
                dest_path = os.path.join(SYSTEM_FONT_PATH, filename)

                copy_cmd = f"cp \"{self.selected_font_path}\" \"{dest_path}\""

                proc = subprocess.Popen(['sudo', '-S', 'bash', '-c', copy_cmd],
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE)
                stdout, stderr = proc.communicate(password.encode())

                if proc.returncode != 0:
                    progress.close()
                    QMessageBox.critical(self, "Installation Failed", f"Error copying file:\n{stderr.decode()}")
                    return

                cache_cmd = "fc-cache -f"
                proc = subprocess.Popen(['sudo', '-S', 'bash', '-c', cache_cmd],
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                proc.communicate(password.encode())

                progress.close()
                QMessageBox.information(self, "Success", f"Font '{filename}' installed successfully!")

                self.check_install_status()

            except Exception as e:
                progress.close()
                QMessageBox.critical(self, "Error", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = FontViewerApp()
    viewer.show()
    sys.exit(app.exec_())
