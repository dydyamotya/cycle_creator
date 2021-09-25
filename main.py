from PySide2 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import logging
import numpy as np
import pathlib

from PySide2.QtCore import QSettings
from PySide2.QtWidgets import QAction

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


class MyMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = QSettings("MotyaSoft", "CycleCreator")
        self._init_gui()

    def _init_gui(self):
        self.central_widget = MyWidget(self)
        self.setCentralWidget(self.central_widget)

        menubar = self.menuBar()
        operations_menu = menubar.addMenu("Operations")
        fill_table_action = QAction("Fill Table", self)
        fill_table_action.setShortcut("Ctrl+F")
        fill_table_action.triggered.connect(self.central_widget.quick_fill_table)
        operations_menu.addAction(fill_table_action)

    def closeEvent(self, event:QtGui.QCloseEvent) -> None:
        self.settings.setValue("freq", self.central_widget.freq_lineedit.text())

class MyWidget(QtWidgets.QWidget):
    def __init__(self, *args):
        super(MyWidget, self).__init__(*args)
        self._init_gui()

    def _init_gui(self):
        settings = self.parent().settings
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)
        table_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(table_layout)

        lineedit_layout = QtWidgets.QHBoxLayout()
        table_layout.addLayout(lineedit_layout)
        self.freq_lineedit = QtWidgets.QLineEdit(settings.value("freq", "10"))
        lineedit_layout.addWidget(QtWidgets.QLabel(text="Frequency, Hz"))
        lineedit_layout.addWidget(self.freq_lineedit)


        buttons_layout = QtWidgets.QHBoxLayout()
        table_layout.addLayout(buttons_layout)

        self.save_button = QtWidgets.QPushButton(text="Save")
        buttons_layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_data)
        self.open_button = QtWidgets.QPushButton(text="Open")
        buttons_layout.addWidget(self.open_button)

        self.generate_button = QtWidgets.QPushButton(self, text="Generate")
        self.generate_button.clicked.connect(self.generate_file)
        buttons_layout.addWidget(self.generate_button)

        self.table = MyTableWidget(self)
        table_layout.addWidget(self.table)
        self.table.cellChanged.connect(self.replot)

        self.plot = MyPlotWidget(self)
        main_layout.addWidget(self.plot)

    def generate_file(self):
        data = self.process_data(self.table.collect_data())
        self._save_data(data, "Save data", "DAT files (*.dat)")


    def save_data(self):
        data = self.table.collect_data()
        self._save_data(data, "Save curve", "TSV files (*.tsv)")

    def _save_data(self, data, widget_name, filters):
        if data is None:
            return None
        folder_name = 'dat_folder' if widget_name == "Save data" else "tsv_folder"
        folder = self.parent().settings.value(folder_name, pathlib.Path.home().as_posix())
        filename, filename_filters = QtWidgets.QFileDialog.getSaveFileName(self, widget_name, folder, filters)
        logger.debug(filename)
        if filename:
            self.parent().settings.setValue(folder_name, pathlib.Path(filename).parent.as_posix())
            # noinspection PyTypeChecker
            np.savetxt(filename, data, delimiter="\t", fmt="%.3f")

    def process_data(self, data):
        little_add = 0.01
        freq_text = self.freq_lineedit.text()
        if not freq_text:
            error_message = QtWidgets.QErrorMessage(parent=self)
            error_message.showMessage("Specify frequency")
            return None
        else:
            freq = int(freq_text)
            period = 1 / freq
            rows, cols = data.shape
            x_list = []
            y_list = []
            for row in range(rows):
                if row == 0:
                    xs = np.arange(0, data[row, 0], period) + little_add
                else:
                    xs = np.arange(data[row-1, 0], data[row, 0], period) + little_add
                ys = np.ones(xs.shape) * data[row, 1]
                x_list.append(xs)
                y_list.append(ys)
            new_data = np.vstack((np.hstack(x_list), np.hstack(y_list))).T

            return new_data

    def open_data(self):
        folder = self.parent().settings.value("tsv_folder", pathlib.Path.home().as_posix())
        filename, filename_filters = QtWidgets.QFileDialog.getOpenFileName(self, "Open curve", folder, ("TSV File (*.tsv *.txt)"))
        if filename:
            self.parent().settings.setValue("tsv_folder", pathlib.Path(filename).parent.as_posix())
            data = np.loadtxt(filename, delimiter="\t")
            self.table.fill_data(data)

    def replot(self):
        logger.debug("Replot")
        try:
            data = self.process_data(self.table.collect_data())
            self.plot.plot_table_contents((data[:, 0], data[:, 1]))
        except ValueError:
            pass

    def quick_fill_table(self):
        top_window = QtWidgets.QWidget(self, QtCore.Qt.Tool)
        self._lineedits = []
        form_layout = QtWidgets.QFormLayout()
        top_window.setLayout(form_layout)
        fields = ("Ширина полки", "Нижняя температура", "Верхняя температура", "Шаг по температуре", "Макс. интервал")
        for field in fields:
            lineedit = QtWidgets.QLineEdit(self)
            form_layout.addRow(field, lineedit)
            self._lineedits.append(lineedit)

        go_button = QtWidgets.QPushButton(self, text="Fill")
        form_layout.addWidget(go_button)
        go_button.clicked.connect(self._on_quick_fill_table)
        go_button.clicked.connect(top_window.close)
        top_window.show()

    def _on_quick_fill_table(self):
        numbers_texts = map(lambda x: x.text(), self._lineedits)
        try:
            numbers = map(int, numbers_texts)
            int(self.freq_lineedit.text())
        except ValueError:
            error_message = QtWidgets.QErrorMessage(parent=self)
            error_message.showMessage("Specify all fields and frequency")
            return None
        else:
            width, low_temp, high_temp, step, max_interval = numbers
            result_list = []
            timer = 1
            for temp in range(low_temp, high_temp, step):
                actual_high = temp + step
                actual_low = max(low_temp, actual_high - max_interval)
                for temp_ in (actual_low, actual_high):
                    result_list.append((timer*width, temp_))
                    timer += 1

            data = np.array(result_list)
            self.table.fill_data(data)









class MyPlotWidget(pg.PlotWidget):
    def __init__(self, *args):
        super(MyPlotWidget, self).__init__(*args)
        self.curve = self.plot()

    def plot_table_contents(self, table_data):
        x, y = table_data
        self.curve.setData(x=x, y=y)


class MyTableWidget(QtWidgets.QTableWidget):
    def __init__(self, *args):
        super(MyTableWidget, self).__init__(50, 2, *args)

    def collect_data(self):
        rows = self.rowCount()
        cols = self.columnCount()
        data = np.empty((rows, cols), dtype=np.int32)
        for row in range(rows):
            for col in range(cols):
                item = self.item(row, col)
                try:
                    data[row, col] = int(item.text())
                except AttributeError:
                    return data[:row]
                except ValueError:
                    return data[:row]


    def fill_data(self, data):
        rows, cols = data.shape
        for row in range(rows):
            for col in range(cols):
                self.setItem(row, col, QtWidgets.QTableWidgetItem(str(int(data[row, col]))))


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = MyMainWindow()
    main_window.show()

    app.exec_()
