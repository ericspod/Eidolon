# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/ChooseSeries.ui'
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

class Ui_ChooseSeriesDialog(object):
    def setupUi(self, ChooseSeriesDialog):
        ChooseSeriesDialog.setObjectName(_fromUtf8("ChooseSeriesDialog"))
        ChooseSeriesDialog.resize(348, 446)
        self.verticalLayout = QtGui.QVBoxLayout(ChooseSeriesDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.choose = QtGui.QGroupBox(ChooseSeriesDialog)
        self.choose.setObjectName(_fromUtf8("choose"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.choose)
        self.horizontalLayout.setMargin(9)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.dirEdit = QtGui.QLineEdit(self.choose)
        self.dirEdit.setReadOnly(True)
        self.dirEdit.setObjectName(_fromUtf8("dirEdit"))
        self.horizontalLayout.addWidget(self.dirEdit)
        self.chooseDirButton = QtGui.QPushButton(self.choose)
        self.chooseDirButton.setObjectName(_fromUtf8("chooseDirButton"))
        self.horizontalLayout.addWidget(self.chooseDirButton)
        self.verticalLayout.addWidget(self.choose)
        self.groupBox = QtGui.QGroupBox(ChooseSeriesDialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.seriesList = QtGui.QListWidget(self.groupBox)
        self.seriesList.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        self.seriesList.setObjectName(_fromUtf8("seriesList"))
        self.verticalLayout_2.addWidget(self.seriesList)
        self.verticalLayout.addWidget(self.groupBox)
        self.paramGroup = QtGui.QGroupBox(ChooseSeriesDialog)
        self.paramGroup.setObjectName(_fromUtf8("paramGroup"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.paramGroup)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.verticalLayout.addWidget(self.paramGroup)
        self.buttonBox = QtGui.QDialogButtonBox(ChooseSeriesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ChooseSeriesDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), ChooseSeriesDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), ChooseSeriesDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ChooseSeriesDialog)

    def retranslateUi(self, ChooseSeriesDialog):
        ChooseSeriesDialog.setWindowTitle(_translate("ChooseSeriesDialog", "Choose DICOM Series", None))
        self.choose.setTitle(_translate("ChooseSeriesDialog", "Choose Directory", None))
        self.chooseDirButton.setText(_translate("ChooseSeriesDialog", "&Choose...", None))
        self.groupBox.setTitle(_translate("ChooseSeriesDialog", "Select Series to Import", None))
        self.paramGroup.setTitle(_translate("ChooseSeriesDialog", "Parameters", None))

