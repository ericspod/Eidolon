# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/ChooseHemi.ui'
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

class Ui_ChoosHemi(object):
    def setupUi(self, ChoosHemi):
        ChoosHemi.setObjectName(_fromUtf8("ChoosHemi"))
        ChoosHemi.resize(417, 116)
        self.formLayout = QtGui.QFormLayout(ChoosHemi)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(ChoosHemi)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.nameEdit = QtGui.QLineEdit(ChoosHemi)
        self.nameEdit.setObjectName(_fromUtf8("nameEdit"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.nameEdit)
        self.buttonBox = QtGui.QDialogButtonBox(ChoosHemi)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.formLayout.setWidget(4, QtGui.QFormLayout.FieldRole, self.buttonBox)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.label_2 = QtGui.QLabel(ChoosHemi)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout.addWidget(self.label_2)
        self.radrefine = QtGui.QSpinBox(ChoosHemi)
        self.radrefine.setMinimum(1)
        self.radrefine.setMaximum(10)
        self.radrefine.setProperty("value", 6)
        self.radrefine.setObjectName(_fromUtf8("radrefine"))
        self.horizontalLayout.addWidget(self.radrefine)
        self.label_3 = QtGui.QLabel(ChoosHemi)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout.addWidget(self.label_3)
        self.vertrefine = QtGui.QSpinBox(ChoosHemi)
        self.vertrefine.setMinimum(1)
        self.vertrefine.setMaximum(10)
        self.vertrefine.setProperty("value", 5)
        self.vertrefine.setObjectName(_fromUtf8("vertrefine"))
        self.horizontalLayout.addWidget(self.vertrefine)
        self.formLayout.setLayout(3, QtGui.QFormLayout.FieldRole, self.horizontalLayout)

        self.retranslateUi(ChoosHemi)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), ChoosHemi.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), ChoosHemi.reject)
        QtCore.QMetaObject.connectSlotsByName(ChoosHemi)

    def retranslateUi(self, ChoosHemi):
        ChoosHemi.setWindowTitle(_translate("ChoosHemi", "Choose Hemisphere Properties", None))
        self.label.setText(_translate("ChoosHemi", "Name", None))
        self.label_2.setText(_translate("ChoosHemi", "Radial Refinement ", None))
        self.label_3.setText(_translate("ChoosHemi", " Vertical Refinement ", None))

