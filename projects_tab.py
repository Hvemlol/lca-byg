from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from db import (
    add_line_item,
    create_project,
    delete_line_item,
    delete_project,
    get_project,
    list_epds,
    list_line_items,
    list_projects,
    project_total_gwp,
)

LINE_ITEM_COLUMNS = [
    ("id", "ID"),
    ("product_name", "EPD product"),
    ("epd_number", "EPD number"),
    ("declared_unit", "Declared unit"),
    ("gwp_a1_a3", "GWP A1-A3"),
    ("quantity", "Quantity"),
    ("gwp_contribution", "GWP contribution (kg CO2-eq)"),
]


class AddLineItemDialog(QDialog):
    def __init__(self, epds: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add line item")
        self.setMinimumWidth(480)
        self.selected_epd_id: int | None = None

        self.list = QListWidget()
        for epd in epds:
            item = QListWidgetItem(f"{epd['product_name']} — {epd.get('declared_unit') or ''}")
            item.setData(32, epd["id"])  # Qt.ItemDataRole.UserRole
            self.list.addItem(item)
        self.list.setCurrentRow(0)

        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g. Foundation slab, 120 m3")
        self.quantity = QDoubleSpinBox()
        self.quantity.setRange(0, 1e12)
        self.quantity.setDecimals(4)
        self.quantity.setValue(1.0)
        self.unit_label = QLabel("")

        self.list.currentRowChanged.connect(self._update_unit_label)
        self._update_unit_label(self.list.currentRow())

        form = QFormLayout()
        form.addRow("EPD", self.list)
        form.addRow("Description", self.description_edit)
        form.addRow("Quantity", self.quantity)
        form.addRow("Unit", self.unit_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _update_unit_label(self, row: int) -> None:
        item = self.list.item(row)
        if item is None:
            self.unit_label.setText("")
            return
        unit = item.text().rsplit("—", 1)[-1].strip()
        self.unit_label.setText(unit)

    def _accept(self) -> None:
        item = self.list.currentItem()
        if item is None:
            QMessageBox.warning(self, "Add line item", "Select an EPD first.")
            return
        if self.quantity.value() <= 0:
            QMessageBox.warning(self, "Add line item", "Quantity must be greater than zero.")
            return
        self.selected_epd_id = item.data(32)
        self.accept()


class ProjectsTab(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_project_id: int | None = None

        new_btn = QPushButton("New project")
        new_btn.clicked.connect(self.new_project)
        delete_btn = QPushButton("Delete project")
        delete_btn.clicked.connect(self.delete_current_project)

        self.project_list = QListWidget()
        self.project_list.currentRowChanged.connect(self._project_selected)

        left = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(new_btn)
        row.addWidget(delete_btn)
        left.addLayout(row)
        left.addWidget(self.project_list)

        self.items_table = QTableWidget(0, len(LINE_ITEM_COLUMNS))
        self.items_table.setHorizontalHeaderLabels([label for _, label in LINE_ITEM_COLUMNS])
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        add_item_btn = QPushButton("Add line item…")
        add_item_btn.clicked.connect(self.add_line_item)
        remove_item_btn = QPushButton("Remove line item")
        remove_item_btn.clicked.connect(self.remove_line_item)

        item_row = QHBoxLayout()
        item_row.addWidget(add_item_btn)
        item_row.addWidget(remove_item_btn)
        item_row.addStretch()

        self.total_label = QLabel("Total GWP (A1-A3): —")
        self.total_label.setStyleSheet("font-weight: bold;")

        right = QVBoxLayout()
        right.addLayout(item_row)
        right.addWidget(self.items_table)
        right.addWidget(self.total_label)

        main = QHBoxLayout(self)
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(320)
        main.addWidget(left_widget)
        right_widget = QWidget()
        right_widget.setLayout(right)
        main.addWidget(right_widget, stretch=1)

        self.refresh_projects()

    # --- projects ---

    def refresh_projects(self, select_id: int | None = None) -> None:
        self.project_list.blockSignals(True)
        self.project_list.clear()
        projects = list_projects(self.conn)
        for p in projects:
            item = QListWidgetItem(f"{p['name']}")
            item.setData(32, p["id"])
            self.project_list.addItem(item)
            if select_id is not None and p["id"] == select_id:
                self.project_list.setCurrentItem(item)
        self.project_list.blockSignals(False)
        if select_id is not None:
            self._project_selected(self.project_list.currentRow())
        elif self.project_list.count():
            self.project_list.setCurrentRow(0)
            self._project_selected(0)
        else:
            self._project_selected(-1)

    def new_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Project name:")
        if not ok or not name.strip():
            return
        location, _ = QInputDialog.getText(self, "New project", "Location (optional):")
        project_id = create_project(self.conn, name.strip(), location.strip())
        self.refresh_projects(select_id=project_id)

    def delete_current_project(self) -> None:
        item = self.project_list.currentItem()
        if item is None:
            return
        project_id = item.data(32)
        project = get_project(self.conn, project_id)
        answer = QMessageBox.question(
            self, "Delete project",
            f"Delete project '{project['name']}' and all its line items?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            delete_project(self.conn, project_id)
            self.refresh_projects()

    def _project_selected(self, row: int) -> None:
        item = self.project_list.item(row) if row >= 0 else None
        self.current_project_id = item.data(32) if item else None
        self.refresh_items()

    # --- line items ---

    def refresh_items(self) -> None:
        self.items_table.setRowCount(0)
        if self.current_project_id is None:
            self.total_label.setText("Total GWP (A1-A3): —")
            return
        for li in list_line_items(self.conn, self.current_project_id):
            r = self.items_table.rowCount()
            self.items_table.insertRow(r)
            for c, (col, _) in enumerate(LINE_ITEM_COLUMNS):
                value = li.get(col)
                if col == "gwp_contribution" and value is not None:
                    text = f"{value:,.2f}"
                elif value is None:
                    text = ""
                else:
                    text = str(value)
                self.items_table.setItem(r, c, QTableWidgetItem(text))
        total = project_total_gwp(self.conn, self.current_project_id)
        self.total_label.setText(f"Total GWP (A1-A3): {total:,.2f} kg CO2-eq")

    def add_line_item(self) -> None:
        if self.current_project_id is None:
            QMessageBox.information(self, "Add line item", "Create or select a project first.")
            return
        epds = list_epds(self.conn)
        if not epds:
            QMessageBox.information(self, "Add line item", "No EPDs in the database yet. Import one from the EPDs tab first.")
            return
        dialog = AddLineItemDialog(epds, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            add_line_item(
                self.conn,
                self.current_project_id,
                dialog.selected_epd_id,
                dialog.quantity.value(),
                dialog.description_edit.text().strip(),
            )
            self.refresh_items()

    def remove_line_item(self) -> None:
        row = self.items_table.currentRow()
        if row < 0:
            return
        line_item_id = int(self.items_table.item(row, 0).text())
        delete_line_item(self.conn, line_item_id)
        self.refresh_items()
