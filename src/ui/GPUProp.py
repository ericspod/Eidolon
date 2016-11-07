# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/GPUProp.ui'
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

class Ui_gpuProp(object):
    def setupUi(self, gpuProp):
        gpuProp.setObjectName(_fromUtf8("gpuProp"))
        gpuProp.resize(364, 682)
        self.verticalLayout = QtGui.QVBoxLayout(gpuProp)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(gpuProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setMinimumSize(QtCore.QSize(0, 0))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.srcEdit = QtGui.QTextEdit(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.srcEdit.sizePolicy().hasHeightForWidth())
        self.srcEdit.setSizePolicy(sizePolicy)
        self.srcEdit.setMinimumSize(QtCore.QSize(0, 300))
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Courier"))
        self.srcEdit.setFont(font)
        self.srcEdit.setObjectName(_fromUtf8("srcEdit"))
        self.verticalLayout_2.addWidget(self.srcEdit)
        self.setSrcButton = QtGui.QPushButton(self.groupBox)
        self.setSrcButton.setObjectName(_fromUtf8("setSrcButton"))
        self.verticalLayout_2.addWidget(self.setSrcButton)
        self.undoButton = QtGui.QPushButton(self.groupBox)
        self.undoButton.setObjectName(_fromUtf8("undoButton"))
        self.verticalLayout_2.addWidget(self.undoButton)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtGui.QGroupBox(gpuProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setMinimumSize(QtCore.QSize(30, 0))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.formLayout = QtGui.QFormLayout(self.groupBox_2)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(self.groupBox_2)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.typeBox = QtGui.QComboBox(self.groupBox_2)
        self.typeBox.setObjectName(_fromUtf8("typeBox"))
        self.typeBox.addItem(_fromUtf8(""))
        self.typeBox.addItem(_fromUtf8(""))
        self.typeBox.addItem(_fromUtf8(""))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.typeBox)
        self.label_2 = QtGui.QLabel(self.groupBox_2)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.langEdit = QtGui.QLineEdit(self.groupBox_2)
        self.langEdit.setObjectName(_fromUtf8("langEdit"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.langEdit)
        self.label_3 = QtGui.QLabel(self.groupBox_2)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.entryEdit = QtGui.QLineEdit(self.groupBox_2)
        self.entryEdit.setObjectName(_fromUtf8("entryEdit"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.entryEdit)
        self.label_4 = QtGui.QLabel(self.groupBox_2)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_4)
        self.profEdit = QtGui.QLineEdit(self.groupBox_2)
        self.profEdit.setObjectName(_fromUtf8("profEdit"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.profEdit)
        self.applyButton = QtGui.QPushButton(self.groupBox_2)
        self.applyButton.setObjectName(_fromUtf8("applyButton"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.applyButton)
        self.verticalLayout.addWidget(self.groupBox_2)

        self.retranslateUi(gpuProp)
        QtCore.QMetaObject.connectSlotsByName(gpuProp)

    def retranslateUi(self, gpuProp):
        gpuProp.setWindowTitle(_translate("gpuProp", "Form", None))
        self.groupBox.setTitle(_translate("gpuProp", "Source Code", None))
        self.setSrcButton.setText(_translate("gpuProp", "Set Source", None))
        self.undoButton.setText(_translate("gpuProp", "Undo All Changes", None))
        self.groupBox_2.setTitle(_translate("gpuProp", "Settings", None))
        self.label.setText(_translate("gpuProp", "Type", None))
        self.typeBox.setItemText(0, _translate("gpuProp", "Vertex", None))
        self.typeBox.setItemText(1, _translate("gpuProp", "Fragment", None))
        self.typeBox.setItemText(2, _translate("gpuProp", "Geometry", None))
        self.label_2.setText(_translate("gpuProp", "Language", None))
        self.label_3.setText(_translate("gpuProp", "Entry Point", None))
        self.label_4.setText(_translate("gpuProp", "Profiles", None))
        self.applyButton.setText(_translate("gpuProp", "Apply Changes", None))

