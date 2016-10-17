# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/SeriesProp.ui'
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
        ObjProp.resize(250, 563)
        self.verticalLayout = QtGui.QVBoxLayout(ObjProp)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox_2 = QtGui.QGroupBox(ObjProp)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setContentsMargins(0, -1, 0, -1)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.propTable = QtGui.QTableWidget(self.groupBox_2)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.propTable.sizePolicy().hasHeightForWidth())
        self.propTable.setSizePolicy(sizePolicy)
        self.propTable.setMinimumSize(QtCore.QSize(0, 170))
        self.propTable.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.propTable.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.propTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
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
        self.propTable.horizontalHeader().setStretchLastSection(False)
        self.propTable.verticalHeader().setCascadingSectionResizes(True)
        self.gridLayout_2.addWidget(self.propTable, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.createReprBox = QtGui.QGroupBox(ObjProp)
        self.createReprBox.setAutoFillBackground(False)
        self.createReprBox.setFlat(False)
        self.createReprBox.setCheckable(False)
        self.createReprBox.setObjectName(_fromUtf8("createReprBox"))
        self.formLayout = QtGui.QFormLayout(self.createReprBox)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.allButton = QtGui.QRadioButton(self.createReprBox)
        self.allButton.setChecked(True)
        self.allButton.setObjectName(_fromUtf8("allButton"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.allButton)
        self.selectedButton = QtGui.QRadioButton(self.createReprBox)
        self.selectedButton.setObjectName(_fromUtf8("selectedButton"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.selectedButton)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_4 = QtGui.QLabel(self.createReprBox)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout.addWidget(self.label_4)
        self.firstBox = QtGui.QSpinBox(self.createReprBox)
        self.firstBox.setMaximum(99999)
        self.firstBox.setObjectName(_fromUtf8("firstBox"))
        self.horizontalLayout.addWidget(self.firstBox)
        self.label_5 = QtGui.QLabel(self.createReprBox)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout.addWidget(self.label_5)
        self.lastBox = QtGui.QSpinBox(self.createReprBox)
        self.lastBox.setMinimum(1)
        self.lastBox.setMaximum(99999)
        self.lastBox.setObjectName(_fromUtf8("lastBox"))
        self.horizontalLayout.addWidget(self.lastBox)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.formLayout.setLayout(2, QtGui.QFormLayout.FieldRole, self.horizontalLayout)
        self.createButton = QtGui.QPushButton(self.createReprBox)
        self.createButton.setObjectName(_fromUtf8("createButton"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.createButton)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(-1, -1, -1, 0)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_6 = QtGui.QLabel(self.createReprBox)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.horizontalLayout_2.addWidget(self.label_6)
        self.stepBox = QtGui.QSpinBox(self.createReprBox)
        self.stepBox.setMinimum(1)
        self.stepBox.setMaximum(999)
        self.stepBox.setObjectName(_fromUtf8("stepBox"))
        self.horizontalLayout_2.addWidget(self.stepBox)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.formLayout.setLayout(3, QtGui.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.verticalLayout.addWidget(self.createReprBox)

        self.retranslateUi(ObjProp)
        QtCore.QMetaObject.connectSlotsByName(ObjProp)

    def retranslateUi(self, ObjProp):
        ObjProp.setWindowTitle(_translate("ObjProp", "Form", None))
        self.groupBox_2.setTitle(_translate("ObjProp", "Properties", None))
        item = self.propTable.horizontalHeaderItem(0)
        item.setText(_translate("ObjProp", "Name", None))
        item = self.propTable.horizontalHeaderItem(1)
        item.setText(_translate("ObjProp", "Value", None))
        self.createReprBox.setTitle(_translate("ObjProp", "Create SceneObject", None))
        self.allButton.setText(_translate("ObjProp", "All Images", None))
        self.selectedButton.setText(_translate("ObjProp", "Selected Images By Index", None))
        self.label_4.setText(_translate("ObjProp", "From", None))
        self.label_5.setText(_translate("ObjProp", "to", None))
        self.createButton.setText(_translate("ObjProp", "Create", None))
        self.label_6.setText(_translate("ObjProp", "Step ", None))

