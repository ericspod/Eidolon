# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'src/ui/LightProp.ui'
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

class Ui_LightProp(object):
    def setupUi(self, LightProp):
        LightProp.setObjectName(_fromUtf8("LightProp"))
        LightProp.resize(341, 567)
        self.verticalLayout_2 = QtGui.QVBoxLayout(LightProp)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setContentsMargins(-1, 0, -1, 0)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.visibleBox = QtGui.QCheckBox(LightProp)
        self.visibleBox.setObjectName(_fromUtf8("visibleBox"))
        self.horizontalLayout_4.addWidget(self.visibleBox)
        self.chooseCamlight = QtGui.QPushButton(LightProp)
        self.chooseCamlight.setObjectName(_fromUtf8("chooseCamlight"))
        self.horizontalLayout_4.addWidget(self.chooseCamlight)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.groupBox_2 = QtGui.QGroupBox(LightProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pointRadio = QtGui.QRadioButton(self.groupBox_2)
        self.pointRadio.setObjectName(_fromUtf8("pointRadio"))
        self.horizontalLayout.addWidget(self.pointRadio)
        self.dirRadio = QtGui.QRadioButton(self.groupBox_2)
        self.dirRadio.setObjectName(_fromUtf8("dirRadio"))
        self.horizontalLayout.addWidget(self.dirRadio)
        self.spotRadio = QtGui.QRadioButton(self.groupBox_2)
        self.spotRadio.setObjectName(_fromUtf8("spotRadio"))
        self.horizontalLayout.addWidget(self.spotRadio)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_2.addWidget(self.groupBox_2)
        self.groupBox = QtGui.QGroupBox(LightProp)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.verticalLayout = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.orientedBox = QtGui.QCheckBox(self.groupBox)
        self.orientedBox.setObjectName(_fromUtf8("orientedBox"))
        self.verticalLayout.addWidget(self.orientedBox)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setContentsMargins(-1, 10, -1, -1)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_2.addWidget(self.label_3)
        self.phi = QtGui.QDoubleSpinBox(self.groupBox)
        self.phi.setDecimals(4)
        self.phi.setMinimum(-100.0)
        self.phi.setMaximum(100.0)
        self.phi.setSingleStep(0.314159)
        self.phi.setObjectName(_fromUtf8("phi"))
        self.horizontalLayout_2.addWidget(self.phi)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.theta = QtGui.QDoubleSpinBox(self.groupBox)
        self.theta.setDecimals(4)
        self.theta.setMinimum(-100.0)
        self.theta.setMaximum(100.0)
        self.theta.setSingleStep(0.314159)
        self.theta.setObjectName(_fromUtf8("theta"))
        self.horizontalLayout_2.addWidget(self.theta)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setContentsMargins(-1, -1, -1, 0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.posz = QtGui.QDoubleSpinBox(LightProp)
        self.posz.setDecimals(3)
        self.posz.setMinimum(-100000.0)
        self.posz.setMaximum(100000.0)
        self.posz.setObjectName(_fromUtf8("posz"))
        self.gridLayout.addWidget(self.posz, 3, 0, 1, 1)
        self.label_8 = QtGui.QLabel(LightProp)
        self.label_8.setObjectName(_fromUtf8("label_8"))
        self.gridLayout.addWidget(self.label_8, 0, 0, 1, 1)
        self.posx = QtGui.QDoubleSpinBox(LightProp)
        self.posx.setDecimals(3)
        self.posx.setMinimum(-100000.0)
        self.posx.setMaximum(100000.0)
        self.posx.setObjectName(_fromUtf8("posx"))
        self.gridLayout.addWidget(self.posx, 1, 0, 1, 1)
        self.label_15 = QtGui.QLabel(LightProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_15.sizePolicy().hasHeightForWidth())
        self.label_15.setSizePolicy(sizePolicy)
        self.label_15.setObjectName(_fromUtf8("label_15"))
        self.gridLayout.addWidget(self.label_15, 2, 1, 1, 1)
        self.diry = QtGui.QDoubleSpinBox(LightProp)
        self.diry.setDecimals(3)
        self.diry.setMinimum(-100000.0)
        self.diry.setMaximum(100000.0)
        self.diry.setObjectName(_fromUtf8("diry"))
        self.gridLayout.addWidget(self.diry, 2, 2, 1, 1)
        self.label_14 = QtGui.QLabel(LightProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_14.sizePolicy().hasHeightForWidth())
        self.label_14.setSizePolicy(sizePolicy)
        self.label_14.setMaximumSize(QtCore.QSize(15, 16777215))
        self.label_14.setObjectName(_fromUtf8("label_14"))
        self.gridLayout.addWidget(self.label_14, 1, 1, 1, 1)
        self.posy = QtGui.QDoubleSpinBox(LightProp)
        self.posy.setDecimals(3)
        self.posy.setMinimum(-100000.0)
        self.posy.setMaximum(100000.0)
        self.posy.setObjectName(_fromUtf8("posy"))
        self.gridLayout.addWidget(self.posy, 2, 0, 1, 1)
        self.label_17 = QtGui.QLabel(LightProp)
        self.label_17.setObjectName(_fromUtf8("label_17"))
        self.gridLayout.addWidget(self.label_17, 0, 2, 1, 1)
        self.dirz = QtGui.QDoubleSpinBox(LightProp)
        self.dirz.setDecimals(3)
        self.dirz.setMinimum(-100000.0)
        self.dirz.setMaximum(100000.0)
        self.dirz.setObjectName(_fromUtf8("dirz"))
        self.gridLayout.addWidget(self.dirz, 3, 2, 1, 1)
        self.label_16 = QtGui.QLabel(LightProp)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_16.sizePolicy().hasHeightForWidth())
        self.label_16.setSizePolicy(sizePolicy)
        self.label_16.setObjectName(_fromUtf8("label_16"))
        self.gridLayout.addWidget(self.label_16, 3, 1, 1, 1)
        self.dirx = QtGui.QDoubleSpinBox(LightProp)
        self.dirx.setDecimals(3)
        self.dirx.setMinimum(-100000.0)
        self.dirx.setMaximum(100000.0)
        self.dirx.setObjectName(_fromUtf8("dirx"))
        self.gridLayout.addWidget(self.dirx, 1, 2, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout)
        self.groupBox_3 = QtGui.QGroupBox(LightProp)
        self.groupBox_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.formLayout = QtGui.QFormLayout(self.groupBox_3)
        self.formLayout.setFormAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_4 = QtGui.QLabel(self.groupBox_3)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_4)
        self.label_5 = QtGui.QLabel(self.groupBox_3)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_5)
        self.label_6 = QtGui.QLabel(self.groupBox_3)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_6)
        self.label_7 = QtGui.QLabel(self.groupBox_3)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_7)
        self.lrange = QtGui.QDoubleSpinBox(self.groupBox_3)
        self.lrange.setDecimals(4)
        self.lrange.setMaximum(1000000.0)
        self.lrange.setObjectName(_fromUtf8("lrange"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.lrange)
        self.lconst = QtGui.QDoubleSpinBox(self.groupBox_3)
        self.lconst.setMinimumSize(QtCore.QSize(0, 0))
        self.lconst.setDecimals(4)
        self.lconst.setMinimum(-99.99)
        self.lconst.setObjectName(_fromUtf8("lconst"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.lconst)
        self.linear = QtGui.QDoubleSpinBox(self.groupBox_3)
        self.linear.setDecimals(4)
        self.linear.setMinimum(-99.99)
        self.linear.setProperty("value", 1.0)
        self.linear.setObjectName(_fromUtf8("linear"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.linear)
        self.quad = QtGui.QDoubleSpinBox(self.groupBox_3)
        self.quad.setDecimals(4)
        self.quad.setMinimum(-99.99)
        self.quad.setObjectName(_fromUtf8("quad"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.quad)
        self.verticalLayout_2.addWidget(self.groupBox_3)
        self.groupBox_4 = QtGui.QGroupBox(LightProp)
        self.groupBox_4.setFlat(False)
        self.groupBox_4.setCheckable(False)
        self.groupBox_4.setObjectName(_fromUtf8("groupBox_4"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_10 = QtGui.QLabel(self.groupBox_4)
        self.label_10.setObjectName(_fromUtf8("label_10"))
        self.horizontalLayout_3.addWidget(self.label_10)
        self.falloff = QtGui.QDoubleSpinBox(self.groupBox_4)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.falloff.sizePolicy().hasHeightForWidth())
        self.falloff.setSizePolicy(sizePolicy)
        self.falloff.setDecimals(4)
        self.falloff.setMinimum(-100.0)
        self.falloff.setMaximum(100.0)
        self.falloff.setSingleStep(0.01)
        self.falloff.setProperty("value", 1.0)
        self.falloff.setObjectName(_fromUtf8("falloff"))
        self.horizontalLayout_3.addWidget(self.falloff)
        self.label_9 = QtGui.QLabel(self.groupBox_4)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.horizontalLayout_3.addWidget(self.label_9)
        self.spotangle = QtGui.QDoubleSpinBox(self.groupBox_4)
        self.spotangle.setDecimals(4)
        self.spotangle.setMinimum(0.0)
        self.spotangle.setMaximum(6.2832)
        self.spotangle.setSingleStep(0.3141)
        self.spotangle.setObjectName(_fromUtf8("spotangle"))
        self.horizontalLayout_3.addWidget(self.spotangle)
        spacerItem3 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem3)
        self.verticalLayout_2.addWidget(self.groupBox_4)

        self.retranslateUi(LightProp)
        QtCore.QMetaObject.connectSlotsByName(LightProp)

    def retranslateUi(self, LightProp):
        LightProp.setWindowTitle(_translate("LightProp", "Form", None))
        self.visibleBox.setText(_translate("LightProp", "Visible", None))
        self.chooseCamlight.setText(_translate("LightProp", "Light Color", None))
        self.groupBox_2.setTitle(_translate("LightProp", "Type", None))
        self.pointRadio.setText(_translate("LightProp", "Point", None))
        self.dirRadio.setText(_translate("LightProp", "Directional", None))
        self.spotRadio.setText(_translate("LightProp", "Spot", None))
        self.groupBox.setTitle(_translate("LightProp", "Camera Rotation Angles", None))
        self.orientedBox.setText(_translate("LightProp", "Camera Oriented", None))
        self.label_3.setText(_translate("LightProp", "Up", None))
        self.label_2.setText(_translate("LightProp", "Right", None))
        self.label_8.setText(_translate("LightProp", "Position", None))
        self.label_15.setText(_translate("LightProp", " Y", None))
        self.label_14.setText(_translate("LightProp", " X", None))
        self.label_17.setText(_translate("LightProp", "Direction", None))
        self.label_16.setText(_translate("LightProp", " Z", None))
        self.groupBox_3.setTitle(_translate("LightProp", "Point/Spot Attenuation", None))
        self.label_4.setText(_translate("LightProp", "Range", None))
        self.label_5.setText(_translate("LightProp", "Const", None))
        self.label_6.setText(_translate("LightProp", "Linear", None))
        self.label_7.setText(_translate("LightProp", "Quad", None))
        self.groupBox_4.setTitle(_translate("LightProp", "Spot Angle", None))
        self.label_10.setText(_translate("LightProp", "Falloff", None))
        self.label_9.setText(_translate("LightProp", "Angle", None))

