from PySide2 import QtWidgets
import pyqtgraph as pg
import logging
import numpy as np
import pathlib

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


class MyMainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_gui()

    def _init_gui(self):
        self.central_widget = MyWidget()
        self.setCentralWidget(self.central_widget)


class MyWidget(QtWidgets.QWidget):
    def __init__(self, *args):
        super(MyWidget, self).__init__(*args)
        self._init_gui()

    def _init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)
        table_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(table_layout)

        lineedit_layout = QtWidgets.QHBoxLayout()
        table_layout.addLayout(lineedit_layout)
        self.freq_lineedit = QtWidgets.QLineEdit()
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
        filename, filename_filters = QtWidgets.QFileDialog.getSaveFileName(self, widget_name, pathlib.Path.home().as_posix(), filters)
        logger.debug(filename)
        if filename:
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
                    xs = np.arange(0, data[row, 0], period)
                else:
                    xs = np.arange(data[row-1, 0], data[row, 0], period)
                ys = np.ones(xs.shape) * data[row, 1]
                x_list.append(xs)
                y_list.append(ys)
            new_data = np.vstack((np.hstack(x_list), np.hstack(y_list))).T

            return new_data

    def open_data(self):
        filename, filename_filters = QtWidgets.QFileDialog.getOpenFileName(self, "Open curve", pathlib.Path.home().as_posix(), ("TSV File (*.tsv *.txt)"))
        if filename:
            data = np.loadtxt(filename, delimiter="\t")
            self.table.fill_data(data)

    def replot(self):
        logger.debug("Replot")
        try:
            data = self.process_data(self.table.collect_data())
            self.plot.plot_table_contents((data[:, 0], data[:, 1]))
        except ValueError:
            pass




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
                self.item(row, col).setText(str(int(data[row, col])))


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main_window = MyMainWindow()
    main_window.show()

    app.exec_()
