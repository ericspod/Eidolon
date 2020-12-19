from PyQt5 import QtWidgets

from eidolon.ui import MainWindow, exec_ui, init_ui, load_rc_file

app = init_ui()

app.setStyle("plastique")
sheet = load_rc_file("DefaultUIStyle", ":/css").decode('utf-8')

app.setStyleSheet(sheet)

win = MainWindow()
win.show()

exec_ui(app)
