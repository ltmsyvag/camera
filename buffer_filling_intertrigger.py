#%%
# import pylablib as pll
from pylablib.devices import DCAM
import time
from codetiming import Timer


with DCAM.DCAMCamera() as cam:
    cam.set_trigger_mode("int")
    cam.set_exposure(0.1) # default 0.0082944
    cam.set_roi(1352,1352+240,948,948+240) # full region (2304, 4096)
    cam.start_acquisition(mode="snap", nframes=1)
    cam.wait_for_frame(timeout=None) # 有一张 frame 后马上 exit，进入下一行
    with Timer(): cam.wait_for_frame(timeout=None)
    frame1 = cam.read_oldest_image() # 读取唯一一张 unread frame， 并且将其标记为 read
    with Timer(): cam.wait_for_frame(timeout=None)
    frame2 = cam.read_oldest_image() # 由于 frame1 的读取已经将 buffer 中的唯一一张 frame 标记为 read，因此 frame2 无法读到 unread frame (除非使用 kwarg peek=True)， 其值为 None
    try:
        assert frame2 is None
        print("frame2 is None")
    except AssertionError:
        print("frame2 is good")
    print(cam.get_device_variable("acquired_frames")) # 这是一个总采集 frame 数的 counter, afaik, 在相机开启期间它只可能一直 +1
    time.sleep(0.5)
    print(cam.get_device_variable("acquired_frames")) 

# %%
