# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/ProjProp.ui'
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

class Ui_ProjProp(object):
    def setupUi(self, ProjProp):
        ProjProp.setObjectName(_fromUtf8("ProjProp"))
        ProjProp.resize(331, 327)
        self.verticalLayout = QtGui.QVBoxLayout(ProjProp)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox_3 = QtGui.QGroupBox(ProjProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_3.sizePolicy().hasHeightForWidth())
        self.groupBox_3.setSizePolicy(sizePolicy)
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.formLayout_2 = QtGui.QFormLayout()
        self.formLayout_2.setContentsMargins(-1, 0, -1, -1)
        self.formLayout_2.setObjectName(_fromUtf8("formLayout_2"))
        self.label = QtGui.QLabel(self.groupBox_3)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.nameEdit = QtGui.QLineEdit(self.groupBox_3)
        self.nameEdit.setObjectName(_fromUtf8("nameEdit"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.FieldRole, self.nameEdit)
        self.label_4 = QtGui.QLabel(self.groupBox_3)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_4)
        self.dirEdit = QtGui.QLineEdit(self.groupBox_3)
        self.dirEdit.setReadOnly(True)
        self.dirEdit.setObjectName(_fromUtf8("dirEdit"))
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.FieldRole, self.dirEdit)
        self.verticalLayout_4.addLayout(self.formLayout_2)
        self.chooseLocLayout = QtGui.QHBoxLayout()
        self.chooseLocLayout.setContentsMargins(-1, 0, -1, -1)
        self.chooseLocLayout.setObjectName(_fromUtf8("chooseLocLayout"))
        self.dirButton = QtGui.QPushButton(self.groupBox_3)
        self.dirButton.setObjectName(_fromUtf8("dirButton"))
        self.chooseLocLayout.addWidget(self.dirButton)
        self.chooseLocLabel = QtGui.QLabel(self.groupBox_3)
        self.chooseLocLabel.setObjectName(_fromUtf8("chooseLocLabel"))
        self.chooseLocLayout.addWidget(self.chooseLocLabel)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.chooseLocLayout.addItem(spacerItem)
        self.verticalLayout_4.addLayout(self.chooseLocLayout)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.saveButton = QtGui.QPushButton(ProjProp)
        self.saveButton.setObjectName(_fromUtf8("saveButton"))
        self.verticalLayout.addWidget(self.saveButton)
        self.selObjBox = QtGui.QGroupBox(ProjProp)
        self.selObjBox.setObjectName(_fromUtf8("selObjBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.selObjBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.selTable = QtGui.QTableWidget(self.selObjBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.selTable.sizePolicy().hasHeightForWidth())
        self.selTable.setSizePolicy(sizePolicy)
        self.selTable.setMinimumSize(QtCore.QSize(0, 100))
        self.selTable.setProperty("showDropIndicator", False)
        self.selTable.setDragDropOverwriteMode(False)
        self.selTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.selTable.setShowGrid(False)
        self.selTable.setObjectName(_fromUtf8("selTable"))
        self.selTable.setColumnCount(2)
        self.selTable.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.selTable.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.selTable.setHorizontalHeaderItem(1, item)
        self.selTable.horizontalHeader().setStretchLastSection(True)
        self.selTable.verticalHeader().setVisible(False)
        self.verticalLayout_2.addWidget(self.selTable)
        self.verticalLayout.addWidget(self.selObjBox)

        self.retranslateUi(ProjProp)
        QtCore.QMetaObject.connectSlotsByName(ProjProp)

    def retranslateUi(self, ProjProp):
        ProjProp.setWindowTitle(_translate("ProjProp", "Form", None))
        self.groupBox_3.setTitle(_translate("ProjProp", "Project", None))
        self.label.setText(_translate("ProjProp", "Name", None))
        self.label_4.setText(_translate("ProjProp", "Location", None))
        self.dirButton.setText(_translate("ProjProp", "Choose Location", None))
        self.chooseLocLabel.setText(_translate("ProjProp", "[Project folder stored here]", None))
        self.saveButton.setText(_translate("ProjProp", "Save", None))
        self.selObjBox.setTitle(_translate("ProjProp", "Selected Objects", None))
        item = self.selTable.horizontalHeaderItem(0)
        item.setText(_translate("ProjProp", "Sel", None))
        item = self.selTable.horizontalHeaderItem(1)
        item.setText(_translate("ProjProp", "Object", None))

