# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/RegionGraphWidget.ui'
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

class Ui_RegionGraphWidget(object):
    def setupUi(self, RegionGraphWidget):
        RegionGraphWidget.setObjectName(_fromUtf8("RegionGraphWidget"))
        RegionGraphWidget.resize(773, 564)
        RegionGraphWidget.setStyleSheet(_fromUtf8(""))
        self.gridLayout = QtGui.QGridLayout(RegionGraphWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.scrollArea = QtGui.QScrollArea(RegionGraphWidget)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName(_fromUtf8("scrollArea"))
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 753, 544))
        self.scrollAreaWidgetContents.setObjectName(_fromUtf8("scrollAreaWidgetContents"))
        self.verticalLayout = QtGui.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.checkboxGroup = QtGui.QGroupBox(self.scrollAreaWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkboxGroup.sizePolicy().hasHeightForWidth())
        self.checkboxGroup.setSizePolicy(sizePolicy)
        self.checkboxGroup.setObjectName(_fromUtf8("checkboxGroup"))
        self.gridLayout_2 = QtGui.QGridLayout(self.checkboxGroup)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setContentsMargins(0, 3, 0, 0)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.verticalLayout.addWidget(self.checkboxGroup)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.gridLayout.addWidget(self.scrollArea, 0, 0, 1, 1)

        self.retranslateUi(RegionGraphWidget)
        QtCore.QMetaObject.connectSlotsByName(RegionGraphWidget)

    def retranslateUi(self, RegionGraphWidget):
        RegionGraphWidget.setWindowTitle(_translate("RegionGraphWidget", "Form", None))
        self.checkboxGroup.setTitle(_translate("RegionGraphWidget", "Plot Regions", None))

