import sys
import traceback
import threading
from PyQt5 import QtCore

from eidolon.mathdef import vec3, generate_axes_arrows
from eidolon.ui import MainWindow, exec_ui, init_ui, load_rc_file, CameraWidget, CameraController
from eidolon.renderer import OffscreenCamera, SimpleFigure
from eidolon import config
from eidolon.utils import Future

conf = config.load_config()

app = init_ui()

app.setStyle("plastique")
sheet = load_rc_file("DefaultUIStyle", ":/css").decode('utf-8')

app.setStyleSheet(sheet)

win = MainWindow(conf)

cam = OffscreenCamera("test", 400, 400)

camwidget = CameraWidget(cam)

ctrl = CameraController(cam, vec3.zero, 0, 0, 50)
ctrl.attach_events(camwidget.events)

win.setCentralWidget(camwidget)

verts, inds, norms, colors = generate_axes_arrows(5, 10)

mesh = SimpleFigure("axes", verts, inds, norms, colors)
mesh.attach(cam)

win.show()

import threading


# t=QtCore.QTimer()
#
# def delaycall():
#     print(threading.current_thread())
#
# def create_timer():
#     global t
#
#     t.setSingleShot(True)
#     t.timeout.connect(delaycall)
#     t.start(1)
#
# tt=threading.Thread(target=create_timer)
# tt.start()
# create_timer()


class EventCallHandler(QtCore.QObject):
    def event(self, event):
        event.accept()

        with event.result:
            event.result.set_result(event.func(*event.args, **event.kwargs))

        return True


class EventCall(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, func, args, kwargs):
        super().__init__(self.EVENT_TYPE)
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = Future()

    def post(self):
        QtCore.QCoreApplication.postEvent(EventCallHandler(), self)
        return self.result


class SyncEvent(QtCore.QEvent):
    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self):
        super().__init__(self.EVENT_TYPE)


class SyncCall(QtCore.QObject):
    def __init__(self, func, args, kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = Future()

    def event(self, event):
        event.accept()

        with self.result:
            res = self.func(*self.args, **self.kwargs)
            self.result.set_result(res)

        return True

    def post(self):
        QtCore.QApplication.postEvent(self, SyncEvent())
        return self.result


def evtest():

    print(threading.current_thread())
    return 123


from eidolon.ui.threadsafe_calls import ThreadsafeCall

calls=[]
sc=None

def start():
    global sc
    print(threading.current_thread())
    sc = ThreadsafeCall(evtest, (), {})
    calls.append(sc)
    win.res = sc.post()
    print("Sent")

# start()
tt=threading.Thread(target=start)
tt.daemon=True
tt.start()

tt.join()
print(calls)

exec_ui(app)
