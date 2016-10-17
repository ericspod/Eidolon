# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/ChooseImgStack.ui'
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

class Ui_OpenImgStackDialog(object):
    def setupUi(self, OpenImgStackDialog):
        OpenImgStackDialog.setObjectName(_fromUtf8("OpenImgStackDialog"))
        OpenImgStackDialog.resize(594, 742)
        self.verticalLayout = QtGui.QVBoxLayout(OpenImgStackDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(OpenImgStackDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.dirEdit = QtGui.QLineEdit(OpenImgStackDialog)
        self.dirEdit.setObjectName(_fromUtf8("dirEdit"))
        self.horizontalLayout.addWidget(self.dirEdit)
        self.chooseDirButton = QtGui.QPushButton(OpenImgStackDialog)
        self.chooseDirButton.setObjectName(_fromUtf8("chooseDirButton"))
        self.horizontalLayout.addWidget(self.chooseDirButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_2 = QtGui.QLabel(OpenImgStackDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.regexEdit = QtGui.QLineEdit(OpenImgStackDialog)
        self.regexEdit.setObjectName(_fromUtf8("regexEdit"))
        self.horizontalLayout_2.addWidget(self.regexEdit)
        self.label_3 = QtGui.QLabel(OpenImgStackDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_2.addWidget(self.label_3)
        self.colBox = QtGui.QSpinBox(OpenImgStackDialog)
        self.colBox.setMinimum(-10)
        self.colBox.setMaximum(10)
        self.colBox.setObjectName(_fromUtf8("colBox"))
        self.horizontalLayout_2.addWidget(self.colBox)
        self.reverseCheck = QtGui.QCheckBox(OpenImgStackDialog)
        self.reverseCheck.setObjectName(_fromUtf8("reverseCheck"))
        self.horizontalLayout_2.addWidget(self.reverseCheck)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_4 = QtGui.QLabel(OpenImgStackDialog)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_3.addWidget(self.label_4)
        self.nameEdit = QtGui.QLineEdit(OpenImgStackDialog)
        self.nameEdit.setObjectName(_fromUtf8("nameEdit"))
        self.horizontalLayout_3.addWidget(self.nameEdit)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.fileList = QtGui.QListWidget(OpenImgStackDialog)
        self.fileList.setObjectName(_fromUtf8("fileList"))
        self.verticalLayout.addWidget(self.fileList)
        self.buttonBox = QtGui.QDialogButtonBox(OpenImgStackDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(OpenImgStackDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), OpenImgStackDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), OpenImgStackDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(OpenImgStackDialog)

    def retranslateUi(self, OpenImgStackDialog):
        OpenImgStackDialog.setWindowTitle(_translate("OpenImgStackDialog", "Dialog", None))
        self.label.setText(_translate("OpenImgStackDialog", "Choose Directory", None))
        self.chooseDirButton.setText(_translate("OpenImgStackDialog", "&Choose...", None))
        self.label_2.setText(_translate("OpenImgStackDialog", "Filename Regex", None))
        self.regexEdit.setText(_translate("OpenImgStackDialog", "*.png", None))
        self.label_3.setText(_translate("OpenImgStackDialog", "Sort Column", None))
        self.reverseCheck.setText(_translate("OpenImgStackDialog", "Reverse", None))
        self.label_4.setText(_translate("OpenImgStackDialog", "Object Name", None))

