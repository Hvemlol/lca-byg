import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from db import get_connection, insert_epd, list_epds
from models import EPDRecord
from pipeline import extract_pdf
from settings import clear_api_key, get_api_key, set_api_key

DB_PATH = str(Path.home() / ".lca-byg" / "lca.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    ("id", "ID"),
    ("epd_number", "EPD number"),
    ("product_name", "Product"),
    ("manufacturer", "Manufacturer"),
    ("declared_unit", "Declared unit"),
    ("gwp_a1_a3", "GWP A1-A3"),
    ("gwp_total", "GWP total"),
    ("pdf_year", "Year"),
    ("valid_until", "Valid until"),
    ("country", "Country"),
    ("source_file", "Source file"),
]

FLOAT_FIELDS = {"gwp_a1_a3", "gwp_total"}
INT_FIELDS = {"pdf_year"}


class ExtractionWorker(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, pdf_path: str, model: str, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.model = model

    def run(self) -> None:
        try:
            self.finished.emit(extract_pdf(self.pdf_path, model=self.model))
        except Exception as exc:
            self.failed.emit(str(exc))


class ReviewDialog(QDialog):
    def __init__(self, record: EPDRecord, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Review extraction — {record.source_file}")
        self.setMinimumWidth(520)

        self.editors: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for name, field in EPDRecord.model_fields.items():
            if name == "source_file":
                continue
            editor = QLineEdit("" if getattr(record, name) is None else str(getattr(record, name)))
            form.addRow(field.description or name, editor)
            self.editors[name] = editor

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def edited_record(self) -> EPDRecord:
        values = {}
        for name, editor in self.editors.items():
            raw = editor.text().strip()
            if raw == "":
                values[name] = None
            elif name in FLOAT_FIELDS:
                values[name] = float(raw)
            elif name in INT_FIELDS:
                values[name] = int(raw)
            else:
                values[name] = raw
        source = self.windowTitle().split("—", 1)[1].strip()
        values["source_file"] = source
        return EPDRecord.model_validate(values)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)

        self.key_edit = QLineEdit(get_api_key() or "")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-...")

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("OpenAI API key", self.key_edit)
        layout.addLayout(form)

        row = QHBoxLayout()
        row.addWidget(save_btn)
        row.addWidget(clear_btn)
        row.addStretch()
        row.addWidget(buttons)
        layout.addLayout(row)

    def _save(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Settings", "API key is empty.")
            return
        set_api_key(key)
        QMessageBox.information(self, "Settings", "API key saved to the OS keyring.")

    def _clear(self) -> None:
        clear_api_key()
        self.key_edit.clear()
        QMessageBox.information(self, "Settings", "API key removed.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LCA-byg — EPD library")
        self.resize(1100, 600)

        self.conn = get_connection(DB_PATH)
        self.worker: ExtractionWorker | None = None

        import_btn = QPushButton("Import EPD PDF…")
        import_btn.clicked.connect(self.import_pdf)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search product, manufacturer, EPD number…")
        self.search.textChanged.connect(self.refresh_table)

        top_row = QHBoxLayout()
        top_row.addWidget(import_btn)
        top_row.addWidget(settings_btn)
        top_row.addStretch()
        top_row.addWidget(self.search, stretch=1)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _, label in COLUMNS])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addWidget(self.table)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.refresh_table()

    def refresh_table(self) -> None:
        needle = self.search.text().strip().lower()
        rows = list_epds(self.conn)
        self.table.setRowCount(0)
        for row in rows:
            haystack = " ".join(str(row.get(col) or "") for col, _ in COLUMNS).lower()
            if needle and needle not in haystack:
                continue
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c, (col, _) in enumerate(COLUMNS):
                value = row.get(col)
                self.table.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))
        self.statusBar().showMessage(f"{self.table.rowCount()} EPD(s)")

    def import_pdf(self) -> None:
        if get_api_key() is None:
            answer = QMessageBox.question(
                self,
                "No API key",
                "No OpenAI API key is configured. Open Settings now?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.open_settings()
            return

        pdf_path, _ = QFileDialog.getOpenFileName(self, "Select EPD PDF", "", "PDF files (*.pdf)")
        if not pdf_path:
            return

        self.statusBar().showMessage(f"Extracting {Path(pdf_path).name} — this can take a minute…")
        self.worker = ExtractionWorker(pdf_path, model="gpt-4o-mini", parent=self)
        self.worker.finished.connect(self.on_extracted)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_extracted(self, record: EPDRecord) -> None:
        dialog = ReviewDialog(record, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                edited = dialog.edited_record()
            except ValueError as exc:
                QMessageBox.critical(self, "Invalid values", f"Could not save: {exc}")
                return
            insert_epd(self.conn, edited)
            self.refresh_table()
            self.statusBar().showMessage(f"Saved {edited.product_name}")
        else:
            self.statusBar().showMessage("Extraction discarded")

    def on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Extraction failed", message)
        self.statusBar().showMessage("Extraction failed")

    def open_settings(self) -> None:
        SettingsDialog(self).exec()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
