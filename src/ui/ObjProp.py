# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/ObjProp.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
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

class Ui_ObjProp(object):
    def setupUi(self, ObjProp):
        ObjProp.setObjectName(_fromUtf8("ObjProp"))
        ObjProp.resize(283, 389)
        self.verticalLayout = QtGui.QVBoxLayout(ObjProp)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.propertiesBox = QtGui.QGroupBox(ObjProp)
        self.propertiesBox.setObjectName(_fromUtf8("propertiesBox"))
        self.gridLayout_2 = QtGui.QGridLayout(self.propertiesBox)
        self.gridLayout_2.setContentsMargins(0, -1, 0, -1)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.propTable = QtGui.QTableWidget(self.propertiesBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.propTable.sizePolicy().hasHeightForWidth())
        self.propTable.setSizePolicy(sizePolicy)
        self.propTable.setMinimumSize(QtCore.QSize(0, 170))
        self.propTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.propTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.propTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.propTable.setProperty("showDropIndicator", False)
        self.propTable.setDragDropOverwriteMode(False)
        self.propTable.setAlternatingRowColors(True)
        self.propTable.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
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
        self.propTable.horizontalHeader().setStretchLastSection(True)
        self.propTable.verticalHeader().setCascadingSectionResizes(True)
        self.gridLayout_2.addWidget(self.propTable, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.propertiesBox)
        self.createReprBox = QtGui.QGroupBox(ObjProp)
        self.createReprBox.setAutoFillBackground(False)
        self.createReprBox.setFlat(False)
        self.createReprBox.setCheckable(False)
        self.createReprBox.setObjectName(_fromUtf8("createReprBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.createReprBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.reprTypeLabel = QtGui.QLabel(self.createReprBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.reprTypeLabel.sizePolicy().hasHeightForWidth())
        self.reprTypeLabel.setSizePolicy(sizePolicy)
        self.reprTypeLabel.setObjectName(_fromUtf8("reprTypeLabel"))
        self.horizontalLayout.addWidget(self.reprTypeLabel)
        self.reprsBox = QtGui.QComboBox(self.createReprBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.reprsBox.sizePolicy().hasHeightForWidth())
        self.reprsBox.setSizePolicy(sizePolicy)
        self.reprsBox.setObjectName(_fromUtf8("reprsBox"))
        self.horizontalLayout.addWidget(self.reprsBox)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.paramLayout = QtGui.QVBoxLayout()
        self.paramLayout.setObjectName(_fromUtf8("paramLayout"))
        self.verticalLayout_2.addLayout(self.paramLayout)
        self.createButton = QtGui.QPushButton(self.createReprBox)
        self.createButton.setObjectName(_fromUtf8("createButton"))
        self.verticalLayout_2.addWidget(self.createButton)
        self.verticalLayout.addWidget(self.createReprBox)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(ObjProp)
        QtCore.QMetaObject.connectSlotsByName(ObjProp)

    def retranslateUi(self, ObjProp):
        ObjProp.setWindowTitle(_translate("ObjProp", "Form", None))
        self.propertiesBox.setTitle(_translate("ObjProp", "Properties", None))
        item = self.propTable.horizontalHeaderItem(0)
        item.setText(_translate("ObjProp", "Name", None))
        item = self.propTable.horizontalHeaderItem(1)
        item.setText(_translate("ObjProp", "Value", None))
        self.createReprBox.setTitle(_translate("ObjProp", "Create Representation", None))
        self.reprTypeLabel.setText(_translate("ObjProp", "Type", None))
        self.reprsBox.setToolTip(_translate("ObjProp", "Representation type", None))
        self.createButton.setToolTip(_translate("ObjProp", "Create a new representation of this data object", None))
        self.createButton.setText(_translate("ObjProp", "Create", None))

