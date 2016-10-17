# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/MeasureObjProp.ui'
#
# Created: Mon Oct 17 15:55:12 2016
#      by: PyQt4 UI code generator 4.10.1
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

class Ui_MeasureObjProp(object):
    def setupUi(self, MeasureObjProp):
        MeasureObjProp.setObjectName(_fromUtf8("MeasureObjProp"))
        MeasureObjProp.resize(335, 587)
        self.verticalLayout = QtGui.QVBoxLayout(MeasureObjProp)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox_2 = QtGui.QGroupBox(MeasureObjProp)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setContentsMargins(0, -1, 0, -1)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.propTable = QtGui.QTableWidget(self.groupBox_2)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.propTable.sizePolicy().hasHeightForWidth())
        self.propTable.setSizePolicy(sizePolicy)
        self.propTable.setMinimumSize(QtCore.QSize(0, 120))
        self.propTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.propTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.propTable.setAlternatingRowColors(True)
        self.propTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.propTable.setTextElideMode(QtCore.Qt.ElideNone)
        self.propTable.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.propTable.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        self.propTable.setShowGrid(False)
        self.propTable.setWordWrap(True)
        self.propTable.setObjectName(_fromUtf8("propTable"))
        self.propTable.setColumnCount(2)
        self.propTable.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.propTable.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.propTable.setHorizontalHeaderItem(1, item)
        self.propTable.horizontalHeader().setCascadingSectionResizes(True)
        self.propTable.horizontalHeader().setDefaultSectionSize(100)
        self.propTable.horizontalHeader().setStretchLastSection(False)
        self.propTable.verticalHeader().setCascadingSectionResizes(True)
        self.gridLayout_2.addWidget(self.propTable, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(MeasureObjProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.srcBox = QtGui.QComboBox(MeasureObjProp)
        self.srcBox.setObjectName(_fromUtf8("srcBox"))
        self.horizontalLayout.addWidget(self.srcBox)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.showButton = QtGui.QPushButton(MeasureObjProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.showButton.sizePolicy().hasHeightForWidth())
        self.showButton.setSizePolicy(sizePolicy)
        self.showButton.setObjectName(_fromUtf8("showButton"))
        self.verticalLayout.addWidget(self.showButton)

        self.retranslateUi(MeasureObjProp)
        QtCore.QMetaObject.connectSlotsByName(MeasureObjProp)

    def retranslateUi(self, MeasureObjProp):
        MeasureObjProp.setWindowTitle(_translate("MeasureObjProp", "Form", None))
        self.groupBox_2.setTitle(_translate("MeasureObjProp", "Properties", None))
        item = self.propTable.horizontalHeaderItem(0)
        item.setText(_translate("MeasureObjProp", "Name", None))
        item = self.propTable.horizontalHeaderItem(1)
        item.setText(_translate("MeasureObjProp", "Value", None))
        self.label.setText(_translate("MeasureObjProp", "Source Image", None))
        self.showButton.setText(_translate("MeasureObjProp", "Show Measurement View", None))

