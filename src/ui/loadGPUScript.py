# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/loadGPUScript.ui'
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

class Ui_gpuDialog(object):
    def setupUi(self, gpuDialog):
        gpuDialog.setObjectName(_fromUtf8("gpuDialog"))
        gpuDialog.resize(526, 202)
        self.formLayout = QtGui.QFormLayout(gpuDialog)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(gpuDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(6, QtGui.QFormLayout.FieldRole, self.buttonBox)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.fileEdit = QtGui.QLineEdit(gpuDialog)
        self.fileEdit.setObjectName(_fromUtf8("fileEdit"))
        self.horizontalLayout.addWidget(self.fileEdit)
        self.chooseButton = QtGui.QPushButton(gpuDialog)
        self.chooseButton.setObjectName(_fromUtf8("chooseButton"))
        self.horizontalLayout.addWidget(self.chooseButton)
        self.formLayout.setLayout(0, QtGui.QFormLayout.FieldRole, self.horizontalLayout)
        self.label = QtGui.QLabel(gpuDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.label_2 = QtGui.QLabel(gpuDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.nameEdit = QtGui.QLineEdit(gpuDialog)
        self.nameEdit.setObjectName(_fromUtf8("nameEdit"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.nameEdit)
        self.typeBox = QtGui.QComboBox(gpuDialog)
        self.typeBox.setObjectName(_fromUtf8("typeBox"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.typeBox)
        self.label_3 = QtGui.QLabel(gpuDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.entryEdit = QtGui.QLineEdit(gpuDialog)
        self.entryEdit.setObjectName(_fromUtf8("entryEdit"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.entryEdit)
        self.profilesEdit = QtGui.QLineEdit(gpuDialog)
        self.profilesEdit.setObjectName(_fromUtf8("profilesEdit"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.FieldRole, self.profilesEdit)
        self.label_4 = QtGui.QLabel(gpuDialog)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.LabelRole, self.label_4)
        self.label_5 = QtGui.QLabel(gpuDialog)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.formLayout.setWidget(5, QtGui.QFormLayout.LabelRole, self.label_5)
        self.langEdit = QtGui.QLineEdit(gpuDialog)
        self.langEdit.setObjectName(_fromUtf8("langEdit"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.langEdit)
        self.label_6 = QtGui.QLabel(gpuDialog)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_6)

        self.retranslateUi(gpuDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), gpuDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), gpuDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(gpuDialog)

    def retranslateUi(self, gpuDialog):
        gpuDialog.setWindowTitle(_translate("gpuDialog", "Choose GPU Script File", None))
        self.chooseButton.setText(_translate("gpuDialog", "Choose...", None))
        self.label.setText(_translate("gpuDialog", "Script File:", None))
        self.label_2.setText(_translate("gpuDialog", "Program Name:", None))
        self.label_3.setText(_translate("gpuDialog", "Type:", None))
        self.label_4.setText(_translate("gpuDialog", "Entry Point:", None))
        self.label_5.setText(_translate("gpuDialog", "Profiles", None))
        self.label_6.setText(_translate("gpuDialog", "Language:", None))

