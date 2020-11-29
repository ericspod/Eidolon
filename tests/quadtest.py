
import eidolon
import eidolon.renderer
import eidolon.ui

def main():
    mgr = eidolon.renderer.Manager()
    # cam = mgr.create_camera("test", 400, 400)
    cam = eidolon.renderer.OffscreenCamera(mgr, "test", 400, 400)

    # ctrl = CameraController(cam, vec3.zero, 0, 0, 50)
    #
    # verts = [(0, 0, 0), (10, 0, 0), (0, 0, 10), (10, 0, 10)]
    # inds = [(0, 1, 2), (1, 3, 2)]
    # norms = [(0, 0, 1)] * len(verts)
    # colors = [
    #     (1.0, 0.0, 0.0, 1.0),
    #     (0.0, 1.0, 0.0, 1.0),
    #     (0.0, 0.0, 1.0, 1.0),
    #     (1.0, 1.0, 1.0, 0.0),
    # ]
    # uvs = [(0, 0)] * len(verts)
    #
    # mesh = Mesh("quad", verts, norms, colors, uvs, inds)
    # mesh.attach(cam)
    #
    # # cam.camera.setPos(0, 50, 0)
    # # cam.camera.look_at(0, 0, 0)
    #
    # ctrl.set_camera_position()
    #
    # cm: NodePath = mesh.camnodes[0]
    # cm.set_pos(LVector3(-5, -5, 0))
    #
    # app = QtWidgets.QApplication(sys.argv)
    #
    # camwidget = CameraWidget(mgr, cam, ctrl)
    #
    # appw = QtWidgets.QMainWindow()
    # appw.resize(800, 600)
    # appw.setCentralWidget(camwidget)
    # appw.show()
    #
    # sys.exit(app.exec_())


if __name__ == "__main__":
    main()