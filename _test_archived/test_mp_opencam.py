#%%
import multiprocessing.connection
from pylablib.devices import DCAM
import multiprocessing

def open_close_cam(conn: multiprocessing.connection.Connection):
    cam = DCAM.DCAMCamera()
    cam.open()
    conn.send("cam opened in p")
    cam.close()
    conn.send("cam closed in p")
    conn.close()

if __name__ == '__main__':
    conn_main, conn_child = multiprocessing.Pipe()
    cam = DCAM.DCAMCamera()
    cam.open()
    print("cam opened")
    cam.close()
    print("cam closed")
    p = multiprocessing.Process(target= open_close_cam, args = (conn_child,))
    p.start()
    print(conn_main.recv())
    print(conn_main.recv())
    conn_main.close()
    p.join()
    cam = DCAM.DCAMCamera()
    cam.open()
    print("cam opened again")
    cam.close()
    print("cam closed again")
