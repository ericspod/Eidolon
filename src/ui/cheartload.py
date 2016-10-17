# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/cheartload.ui'
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

class Ui_ObjDialog(object):
    def setupUi(self, ObjDialog):
        ObjDialog.setObjectName(_fromUtf8("ObjDialog"))
        ObjDialog.resize(636, 166)
        ObjDialog.setMaximumSize(QtCore.QSize(16777215, 201))
        self.gridLayout = QtGui.QGridLayout(ObjDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(ObjDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 7, 3, 1, 1)
        self.label = QtGui.QLabel(ObjDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setMaximumSize(QtCore.QSize(16777215, 20))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(ObjDialog)
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 4, 0, 1, 1)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.tfile = QtGui.QLineEdit(ObjDialog)
        self.tfile.setObjectName(_fromUtf8("tfile"))
        self.horizontalLayout_2.addWidget(self.tfile)
        self.tchoose = QtGui.QPushButton(ObjDialog)
        self.tchoose.setObjectName(_fromUtf8("tchoose"))
        self.horizontalLayout_2.addWidget(self.tchoose)
        self.gridLayout.addLayout(self.horizontalLayout_2, 4, 3, 1, 1)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.xfile = QtGui.QLineEdit(ObjDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.xfile.sizePolicy().hasHeightForWidth())
        self.xfile.setSizePolicy(sizePolicy)
        self.xfile.setMinimumSize(QtCore.QSize(0, 0))
        self.xfile.setObjectName(_fromUtf8("xfile"))
        self.horizontalLayout_3.addWidget(self.xfile)
        self.xchoose = QtGui.QPushButton(ObjDialog)
        self.xchoose.setMaximumSize(QtCore.QSize(100, 16777215))
        self.xchoose.setObjectName(_fromUtf8("xchoose"))
        self.horizontalLayout_3.addWidget(self.xchoose)
        self.gridLayout.addLayout(self.horizontalLayout_3, 3, 3, 1, 1)
        self.widget = QtGui.QWidget(ObjDialog)
        self.widget.setObjectName(_fromUtf8("widget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_5 = QtGui.QLabel(self.widget)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout.addWidget(self.label_5)
        self.geomBox = QtGui.QComboBox(self.widget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.geomBox.sizePolicy().hasHeightForWidth())
        self.geomBox.setSizePolicy(sizePolicy)
        self.geomBox.setObjectName(_fromUtf8("geomBox"))
        self.horizontalLayout.addWidget(self.geomBox)
        self.label_3 = QtGui.QLabel(self.widget)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout.addWidget(self.label_3)
        self.basisBox = QtGui.QComboBox(self.widget)
        self.basisBox.setObjectName(_fromUtf8("basisBox"))
        self.horizontalLayout.addWidget(self.basisBox)
        self.label_4 = QtGui.QLabel(self.widget)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout.addWidget(self.label_4)
        self.orderBox = QtGui.QSpinBox(self.widget)
        self.orderBox.setMinimum(1)
        self.orderBox.setMaximum(20)
        self.orderBox.setObjectName(_fromUtf8("orderBox"))
        self.horizontalLayout.addWidget(self.orderBox)
        self.gridLayout.addWidget(self.widget, 6, 3, 1, 1)

        self.retranslateUi(ObjDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), ObjDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), ObjDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ObjDialog)

    def retranslateUi(self, ObjDialog):
        ObjDialog.setWindowTitle(_translate("ObjDialog", "Choose Cheart Input Files", None))
        self.label.setText(_translate("ObjDialog", "Node File (*.X):", None))
        self.label_2.setText(_translate("ObjDialog", "Topology File (*.T):", None))
        self.tchoose.setText(_translate("ObjDialog", "C&hoose...", None))
        self.xchoose.setText(_translate("ObjDialog", "&Choose...", None))
        self.label_5.setText(_translate("ObjDialog", "Geometry:", None))
        self.label_3.setText(_translate("ObjDialog", "Basis Function:", None))
        self.label_4.setText(_translate("ObjDialog", "Order:", None))

