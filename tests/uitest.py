from PyQt5 import QtWidgets

from eidolon.ui import MainWindow, exec_ui, init_ui

app = init_ui()

app.setStyle("Plastique")
app.setStyleSheet(open("../res/DefaultUIStyle.css").read())

win = MainWindow()
win.show()

exec_ui(app)
