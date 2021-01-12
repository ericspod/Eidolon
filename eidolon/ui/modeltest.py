import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt

from eidolon.ui import DictTableModel, ComboBoxModel


class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            # See below for the nested-list data structure.
            # .row() indexes into the outer list,
            # .column() indexes into the sub-list
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        # The length of the outer list.
        return len(self._data)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self._data[0])


class TupleTreeModel(QtGui.QStandardItemModel):
    def __init__(self, data):
        super().__init__()
        self._data = []

        self.fill(data)

    def fill(self,data):
        self.clear()
        self._data[:]=data

        for idx in range(len(self._data)):
            item=self._get_item(idx)

            self.appendRow(item)

    def _get_item(self, idx):
        def _create_item(value, children, parent: QtGui.QStandardItem = None):
            item = QtGui.QStandardItem(value)
            if parent is not None:
                parent.appendRow([item])

            for v, c in children:
                _create_item(v, c, item)

            return item

        return _create_item(*self._data[idx])

    # def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
    #     return len(self._data)
    #
    # def columnCount(self, parent=None) -> int:
    #     return 1
    #
    # def data(self, index: QtCore.QModelIndex, role: int = ...):
    #     if index.isValid() and role == QtCore.Qt.DisplayRole:
    #         return self._get_item(index.row())


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # self.table = QtWidgets.QTableView()
        #
        # data = [
        #     [4, 9, 2],
        #     [1, 0, 0],
        #     [3, 5, 0],
        #     [3, 3, 2],
        #     [7, 8, 9],
        # ]
        #
        # self.table.setModel(DictTableModel({"Foo":1,"Bar":2}))
        #
        # self.setCentralWidget(self.table)

        # self.model = ComboBoxModel()
        #
        # self.combo = QtWidgets.QComboBox()
        #
        # self.model.attach(self.combo)
        #
        # self.setCentralWidget(self.combo)
        #
        # self.model._data[:] = ["foo", "bar"]
        #
        # def update():
        #     try:
        #         # self.model._data[:] = ["thunk","foo", "bar"]
        #         # self.model.modelReset.emit()
        #
        #         self.model.replace(["thunk", "foo", "bar"])
        #     except Exception as e:
        #         print(e)
        #
        # self.timer = QtCore.QTimer()
        # self.timer.setSingleShot(True)
        # self.timer.setInterval(5000)
        # self.timer.timeout.connect(update)
        # self.timer.start()

        self.model = TupleTreeModel([
            ("foo", ()),
            ("bar", (
                ("baz", ()),
                ("thunk", ())
            ))
        ])

        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.setCentralWidget(self.tree)


app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
