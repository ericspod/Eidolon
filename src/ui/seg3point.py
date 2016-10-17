# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/seg3point.ui'
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

class Ui_Seg3Point(object):
    def setupUi(self, Seg3Point):
        Seg3Point.setObjectName(_fromUtf8("Seg3Point"))
        Seg3Point.resize(665, 190)
        self.gridLayout = QtGui.QGridLayout(Seg3Point)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.ptBox = QtGui.QGroupBox(Seg3Point)
        self.ptBox.setStyleSheet(_fromUtf8(""))
        self.ptBox.setObjectName(_fromUtf8("ptBox"))
        self.gridLayout_2 = QtGui.QGridLayout(self.ptBox)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.rvAPlaneButton = QtGui.QPushButton(self.ptBox)
        self.rvAPlaneButton.setObjectName(_fromUtf8("rvAPlaneButton"))
        self.gridLayout_2.addWidget(self.rvAPlaneButton, 3, 1, 1, 1)
        self.label_4 = QtGui.QLabel(self.ptBox)
        self.label_4.setStyleSheet(_fromUtf8("background-color:rgb(0,0,255,120);"))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout_2.addWidget(self.label_4, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self.ptBox)
        self.label_2.setStyleSheet(_fromUtf8("background-color:rgb(0,255,0,120);"))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)
        self.label_3 = QtGui.QLabel(self.ptBox)
        self.label_3.setStyleSheet(_fromUtf8("background-color:rgb(0,0,255,120);"))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout_2.addWidget(self.label_3, 2, 0, 1, 1)
        self.lvPlaneButton = QtGui.QPushButton(self.ptBox)
        self.lvPlaneButton.setObjectName(_fromUtf8("lvPlaneButton"))
        self.gridLayout_2.addWidget(self.lvPlaneButton, 0, 1, 1, 1)
        self.apexPlaneButton = QtGui.QPushButton(self.ptBox)
        self.apexPlaneButton.setObjectName(_fromUtf8("apexPlaneButton"))
        self.gridLayout_2.addWidget(self.apexPlaneButton, 1, 1, 1, 1)
        self.rvPlaneButton = QtGui.QPushButton(self.ptBox)
        self.rvPlaneButton.setObjectName(_fromUtf8("rvPlaneButton"))
        self.gridLayout_2.addWidget(self.rvPlaneButton, 2, 1, 1, 1)
        self.label = QtGui.QLabel(self.ptBox)
        self.label.setStyleSheet(_fromUtf8("background-color: rgb(255,0,0,120);"))
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout_2.addWidget(self.label, 0, 0, 1, 1)
        self.lvEdit = QtGui.QLineEdit(self.ptBox)
        self.lvEdit.setReadOnly(True)
        self.lvEdit.setObjectName(_fromUtf8("lvEdit"))
        self.gridLayout_2.addWidget(self.lvEdit, 0, 2, 1, 1)
        self.apexEdit = QtGui.QLineEdit(self.ptBox)
        self.apexEdit.setReadOnly(True)
        self.apexEdit.setObjectName(_fromUtf8("apexEdit"))
        self.gridLayout_2.addWidget(self.apexEdit, 1, 2, 1, 1)
        self.rvEdit = QtGui.QLineEdit(self.ptBox)
        self.rvEdit.setReadOnly(True)
        self.rvEdit.setObjectName(_fromUtf8("rvEdit"))
        self.gridLayout_2.addWidget(self.rvEdit, 2, 2, 1, 1)
        self.rvPPlaneButton = QtGui.QPushButton(self.ptBox)
        self.rvPPlaneButton.setObjectName(_fromUtf8("rvPPlaneButton"))
        self.gridLayout_2.addWidget(self.rvPPlaneButton, 4, 1, 1, 1)
        self.rvAEdit = QtGui.QLineEdit(self.ptBox)
        self.rvAEdit.setReadOnly(True)
        self.rvAEdit.setObjectName(_fromUtf8("rvAEdit"))
        self.gridLayout_2.addWidget(self.rvAEdit, 3, 2, 1, 1)
        self.rvPEdit = QtGui.QLineEdit(self.ptBox)
        self.rvPEdit.setReadOnly(True)
        self.rvPEdit.setObjectName(_fromUtf8("rvPEdit"))
        self.gridLayout_2.addWidget(self.rvPEdit, 4, 2, 1, 1)
        self.label_5 = QtGui.QLabel(self.ptBox)
        self.label_5.setStyleSheet(_fromUtf8("background-color:rgb(0,255,255,120);"))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout_2.addWidget(self.label_5, 4, 0, 1, 1)
        self.gridLayout.addWidget(self.ptBox, 0, 0, 1, 1)

        self.retranslateUi(Seg3Point)
        QtCore.QMetaObject.connectSlotsByName(Seg3Point)

    def retranslateUi(self, Seg3Point):
        Seg3Point.setWindowTitle(_translate("Seg3Point", "Form", None))
        self.ptBox.setTitle(_translate("Seg3Point", "3 Point Segmentation Values", None))
        self.rvAPlaneButton.setText(_translate("Seg3Point", "Set Plane", None))
        self.label_4.setText(_translate("Seg3Point", "RV Anterior", None))
        self.label_2.setText(_translate("Seg3Point", " Apex", None))
        self.label_3.setText(_translate("Seg3Point", " RV Top ", None))
        self.lvPlaneButton.setText(_translate("Seg3Point", "Set Plane", None))
        self.apexPlaneButton.setText(_translate("Seg3Point", "Set Plane", None))
        self.rvPlaneButton.setText(_translate("Seg3Point", "Set Plane", None))
        self.label.setText(_translate("Seg3Point", " LV Top", None))
        self.rvPPlaneButton.setText(_translate("Seg3Point", "Set Plane", None))
        self.label_5.setText(_translate("Seg3Point", "RV Posterior", None))

