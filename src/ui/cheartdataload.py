# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/cheartdataload.ui'
#
# Created: Fri Apr 15 18:19:53 2016
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_DataDialog(object):
    def setupUi(self, DataDialog):
        DataDialog.setObjectName(_fromUtf8("DataDialog"))
        DataDialog.resize(806, 399)
        self.verticalLayout = QtGui.QVBoxLayout(DataDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_4 = QtGui.QLabel(DataDialog)
        self.label_4.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_2.addWidget(self.label_4)
        self.tfile = QtGui.QLineEdit(DataDialog)
        self.tfile.setObjectName(_fromUtf8("tfile"))
        self.horizontalLayout_2.addWidget(self.tfile)
        self.tchoose = QtGui.QPushButton(DataDialog)
        self.tchoose.setObjectName(_fromUtf8("tchoose"))
        self.horizontalLayout_2.addWidget(self.tchoose)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem)
        self.label_5 = QtGui.QLabel(DataDialog)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout_5.addWidget(self.label_5)
        self.geomBox = QtGui.QComboBox(DataDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.geomBox.sizePolicy().hasHeightForWidth())
        self.geomBox.setSizePolicy(sizePolicy)
        self.geomBox.setObjectName(_fromUtf8("geomBox"))
        self.horizontalLayout_5.addWidget(self.geomBox)
        self.label_8 = QtGui.QLabel(DataDialog)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.horizontalLayout_5.addWidget(self.label_8)
        self.basisBox = QtGui.QComboBox(DataDialog)
        self.basisBox.setObjectName(_fromUtf8("basisBox"))
        self.horizontalLayout_5.addWidget(self.basisBox)
        self.label_7 = QtGui.QLabel(DataDialog)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.horizontalLayout_5.addWidget(self.label_7)
        self.orderBox = QtGui.QSpinBox(DataDialog)
        self.orderBox.setMinimum(1)
        self.orderBox.setMaximum(20)
        self.orderBox.setObjectName(_fromUtf8("orderBox"))
        self.horizontalLayout_5.addWidget(self.orderBox)
        self.verticalLayout.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_3 = QtGui.QLabel(DataDialog)
        self.label_3.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_3.addWidget(self.label_3)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.dchoose = QtGui.QPushButton(DataDialog)
        self.dchoose.setObjectName(_fromUtf8("dchoose"))
        self.horizontalLayout_3.addWidget(self.dchoose)
        self.label = QtGui.QLabel(DataDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.dimBox = QtGui.QSpinBox(DataDialog)
        self.dimBox.setMinimum(1)
        self.dimBox.setObjectName(_fromUtf8("dimBox"))
        self.horizontalLayout_3.addWidget(self.dimBox)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.dfileTable = QtGui.QTableWidget(DataDialog)
        self.dfileTable.setObjectName(_fromUtf8("dfileTable"))
        self.dfileTable.setColumnCount(2)
        self.dfileTable.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.dfileTable.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.dfileTable.setHorizontalHeaderItem(1, item)
        self.dfileTable.horizontalHeader().setStretchLastSection(True)
        self.verticalLayout.addWidget(self.dfileTable)
        self.buttonBox = QtGui.QDialogButtonBox(DataDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(DataDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), DataDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), DataDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(DataDialog)

    def retranslateUi(self, DataDialog):
        DataDialog.setWindowTitle(_translate("DataDialog", "Choose Cheart Input Files", None))
        self.label_4.setText(_translate("DataDialog", "Topology File (*.T):", None))
        self.tchoose.setText(_translate("DataDialog", "&Choose...", None))
        self.label_5.setText(_translate("DataDialog", "Geometry:", None))
        self.label_8.setText(_translate("DataDialog", "Basis Function:", None))
        self.label_7.setText(_translate("DataDialog", "Order:", None))
        self.label_3.setText(_translate("DataDialog", "Data Files (*.D):", None))
        self.dchoose.setText(_translate("DataDialog", "&Add Field Files...", None))
        self.label.setText(_translate("DataDialog", "Data Dimensions:", None))
        item = self.dfileTable.horizontalHeaderItem(0)
        item.setText(_translate("DataDialog", "#", None))
        item = self.dfileTable.horizontalHeaderItem(1)
        item.setText(_translate("DataDialog", "Filenames", None))

