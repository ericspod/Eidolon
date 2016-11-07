# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/ShowMsg.ui'
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

class Ui_ShowMsg(object):
    def setupUi(self, ShowMsg):
        ShowMsg.setObjectName(_fromUtf8("ShowMsg"))
        ShowMsg.resize(400, 300)
        self.verticalLayout = QtGui.QVBoxLayout(ShowMsg)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.msgLabel = QtGui.QLabel(ShowMsg)
        self.msgLabel.setObjectName(_fromUtf8("msgLabel"))
        self.verticalLayout.addWidget(self.msgLabel)
        self.textEdit = QtGui.QTextEdit(ShowMsg)
        self.textEdit.setObjectName(_fromUtf8("textEdit"))
        self.verticalLayout.addWidget(self.textEdit)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.prevButton = QtGui.QPushButton(ShowMsg)
        self.prevButton.setMaximumSize(QtCore.QSize(20, 16777215))
        self.prevButton.setObjectName(_fromUtf8("prevButton"))
        self.horizontalLayout.addWidget(self.prevButton)
        self.countLabel = QtGui.QLabel(ShowMsg)
        self.countLabel.setMinimumSize(QtCore.QSize(100, 0))
        self.countLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.countLabel.setObjectName(_fromUtf8("countLabel"))
        self.horizontalLayout.addWidget(self.countLabel)
        self.nextButton = QtGui.QPushButton(ShowMsg)
        self.nextButton.setMaximumSize(QtCore.QSize(20, 16777215))
        self.nextButton.setObjectName(_fromUtf8("nextButton"))
        self.horizontalLayout.addWidget(self.nextButton)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.closeButton = QtGui.QPushButton(ShowMsg)
        self.closeButton.setObjectName(_fromUtf8("closeButton"))
        self.horizontalLayout.addWidget(self.closeButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(ShowMsg)
        QtCore.QMetaObject.connectSlotsByName(ShowMsg)

    def retranslateUi(self, ShowMsg):
        ShowMsg.setWindowTitle(_translate("ShowMsg", "Dialog", None))
        self.msgLabel.setText(_translate("ShowMsg", "Msg", None))
        self.prevButton.setText(_translate("ShowMsg", "<", None))
        self.countLabel.setText(_translate("ShowMsg", "Message 0/0", None))
        self.nextButton.setText(_translate("ShowMsg", ">", None))
        self.closeButton.setText(_translate("ShowMsg", "Close", None))

import Resources_rc
