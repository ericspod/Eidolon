# Eidolon Biomedical Framework
# Copyright (C) 2016-20 Eric Kerfoot, King's College London, all rights reserved
#
# This file is part of Eidolon.
#
# Eidolon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Eidolon is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program (LICENSE.txt).  If not, see <http://www.gnu.org/licenses/>


import contextlib
from functools import partial
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt


def to_qt_color(c):
    """Converts an iterable object yielding color channel unit float values to a QColor."""
    if isinstance(c, QtGui.QColor):
        return c
    else:
        c = list(c)
        c += [1.0] * (4 - len(c))
        return QtGui.QColor(c[0] * 255, c[1] * 255, c[2] * 255, c[3] * 255)


def traverse_widget(widg, func=lambda i: True):
    found = set([widg])
    widgstack = [widg]

    while widgstack:
        w = widgstack.pop()
        found.add(w)
        for d in dir(w):
            obj = getattr(w, d)
            try:
                if obj not in found and isinstance(obj, QtWidgets.QWidget) and func(obj):
                    widgstack.push(obj)
            except:
                pass


@contextlib.contextmanager
def signal_blocker(*objs):
    """Blocks signals going to the given argument objects within the scope of the block."""
    origvals = [o.blockSignals(True) for o in objs]
    yield  # execute code in 'with' block
    for o, v in zip(objs, origvals):
        o.blockSignals(v)


def get_wheel_delta(qwheelevent):
    """Returns a wheel scroll delta value combining the X and Y axes."""
    delta = qwheelevent.angleDelta()
    return delta.y() or delta.x() * -1


def select_box_index(val, box):
    """Set the current index in `box' to be the first item whose text is `val', returning True if this was done."""
    with signal_blocker(box):
        for i in range(box.count()):
            if str(box.itemText(i)) == val:
                box.setCurrentIndex(i)
                return True

    return False


def set_collapsible_groupbox(box, is_visible=True):
    """
    Transforms the QGroupBox `box' into a collapsible one, which will have a check box that collapses its contents if
    unchecked. The box will be initially collapsed if `isVisible' is False.
    """
    w = QtWidgets.QWidget()
    w.setLayout(box.layout())
    w.setContentsMargins(0, 0, 0, 0)
    w.setStyleSheet('.QWidget{background-color:0x00000000;}')
    box.setStyleSheet('.QGroupBox::title { padding-left:-1px; }')
    layout = QtWidgets.QVBoxLayout(box)
    layout.addWidget(w)
    layout.setContentsMargins(0, 0, 0, 0)
    box.setCheckable(True)
    box.setChecked(is_visible)
    w.setVisible(is_visible)
    box.clicked.connect(w.setVisible)


def set_warning_stylesheet(widg):
    """
    Set the stylesheet for `widg' to show a black+yellow striped background indicating advanced/dangerous features.
    """

    sheet = """QGroupBox{
border: 2px solid black;
background-color: qlineargradient(spread:reflect, x1:0, y1:0, x2:0.037, y2:0.006, stop:0.475271 rgba(50, 50, 50, 255), stop:0.497948 rgba(150, 150, 0, 255));
}
QGroupBox::indicator { background-color:rgba(0,0,0,150.0); border:0;}
QGroupBox::title { background-color:rgba(0,0,0,150.0); }
QLabel { background-color:rgba(0,0,0,150.0); padding:1px;}"""
    widg.setStyleSheet(sheet)


def center_window(wind):
    """Centers the window `wind' on the desktop by moving it only."""
    geom = wind.geometry()
    geom.moveCenter(QtWidgets.QDesktopWidget().availableGeometry().center())
    wind.move(geom.topLeft())


def resize_screen_relative(wind, w, h):
    """Resize the window `wind` to fit within the desktop if necessary, leave it unchanged if not."""
    geom = wind.geometry()
    desk = QtWidgets.QDesktopWidget().availableGeometry()
    nw = geom.width()
    nh = geom.height()

    if nw > desk.width():
        nw = int(desk.width() * w)

    if nh > desk.height():
        nh = int(desk.height() * h)

    wind.resize(nw, nh)


def screenshot_widget(w, filename):
    """Save a screenshot of the widget `w' to the file `filename'."""
    try:
        p = QtGui.QPixmap.grabWidget(w)
    except:
        p = w.grab()

    p.save(filename)


def set_checked(is_checked, checkbox):
    """Set the checkable widget `checkbox' to the boolean status `isChecked'."""
    with signal_blocker(checkbox):
        checkbox.setChecked(is_checked)


def set_color_button(col, button):
    """Set the colour of left hand border of `button' to color object `col'."""
    button.setStyleSheet(f"border-left: 5px solid {to_qt_color(col).name()}")


def set_spin_box(box, minval=None, maxval=None, stepval=None, decimals=None):
    with signal_blocker(box):
        if minval is not None:
            box.setMinimum(minval)
        if maxval is not None:
            box.setMaximum(maxval)
        if decimals is not None:
            box.setDecimals(decimals)
        if stepval is not None:
            box.setSingleStep(stepval)


def set_table_headers(table):
    # NOTE: the critical property the table must have is the cascading resize settings must be set to true for both dimensions
    # The designer properties for these are horizontalHeaderCascadingSectionResizes and verticalHeaderCascadingSectionResizes
    table.verticalHeader().setCascadingSectionResizes(True)
    table.horizontalHeader().setCascadingSectionResizes(True)
    table.verticalHeader().setDefaultAlignment(Qt.AlignLeft)  # why doesn't this stick in the designer?
    table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
    table.horizontalHeader().setStretchLastSection(True)


def create_split_widget(parent, widg1, widg2, is_vertical=True):
    """Create a splitter widget within `parent' with `widg1' and `widg2' as its two halves, vertical if `isVertical."""
    split = QtWidgets.QSplitter(parent)
    split.setOrientation(Qt.Vertical if is_vertical else Qt.Horizontal)
    split.setChildrenCollapsible(False)
    widg1.setParent(split)
    widg2.setParent(split)
    return split


def create_menu(title, values, default_func=lambda v: None, parent=None):
    """
    Construct a menu widget from the given values. The list `values` must contain strings, pairs containing strings
    and a callback function, '---' for a separator, or further lists thereof. When a item is selected, the given callback
    function is called with the string passed as an argument, if only a string is given then `default_func` is called
    instead with that string as argument.
    """
    menu = QtWidgets.QMenu(parent)

    if title:
        # menu.setTitle(title)
        menu.addAction(title, lambda: None)
        menu.addSeparator()

    def _call_func(_func, _val):  # needed to ensure v and func are fresh
        return partial(_func, _val)

    for val in values:
        if val == '---':
            menu.addSeparator()
        elif isinstance(val, list):
            menu.addMenu(create_menu('', val, default_func, menu))
        else:
            if isinstance(val, str):
                func = default_func
            else:
                assert isinstance(val, tuple) and len(val) == 2
                val, func = val

            menu.addAction(val, _call_func(func, val))

    return menu


