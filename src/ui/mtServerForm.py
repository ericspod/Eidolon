# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/mtServerForm.ui'
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

class Ui_mtServerForm(object):
    def setupUi(self, mtServerForm):
        mtServerForm.setObjectName(_fromUtf8("mtServerForm"))
        mtServerForm.resize(548, 398)
        self.verticalLayout = QtGui.QVBoxLayout(mtServerForm)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(mtServerForm)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.jobList = QtGui.QListWidget(self.groupBox)
        self.jobList.setObjectName(_fromUtf8("jobList"))
        self.gridLayout.addWidget(self.jobList, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.horizontalGroupBox = QtGui.QGroupBox(mtServerForm)
        self.horizontalGroupBox.setObjectName(_fromUtf8("horizontalGroupBox"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalGroupBox)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.killButton = QtGui.QPushButton(self.horizontalGroupBox)
        self.killButton.setObjectName(_fromUtf8("killButton"))
        self.horizontalLayout.addWidget(self.killButton)
        self.verticalLayout.addWidget(self.horizontalGroupBox)

        self.retranslateUi(mtServerForm)
        QtCore.QMetaObject.connectSlotsByName(mtServerForm)

    def retranslateUi(self, mtServerForm):
        mtServerForm.setWindowTitle(_translate("mtServerForm", "MotionTrackServer", None))
        self.groupBox.setTitle(_translate("mtServerForm", "Active Jobs", None))
        self.horizontalGroupBox.setTitle(_translate("mtServerForm", "Commands", None))
        self.killButton.setToolTip(_translate("mtServerForm", "Kills a running motion track job", None))
        self.killButton.setText(_translate("mtServerForm", "Kill Job", None))

