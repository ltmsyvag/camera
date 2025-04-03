#%% 计时代码。codetiming 计时模组的 overhead 在 150 ns 量级，可忽略
import pylablib as pll
from pylablib.devices import DCAM
from codetiming import Timer
tKey = "progressive3kHz"
tWait = Timer(tKey, logger=None)
with DCAM.DCAMCamera() as cam:
    cam.set_trigger_mode("ext")
    cam.cav["sensor_mode"] = 12
    cam.set_exposure(0) # default 0.0082944
    cam.set_roi(1352,1352+240,948,948+240) # full region (2304, 4096)
    cam.start_acquisition(mode="snap", nframes=100)
    for _ in range(5):
        cam.wait_for_frame()
        frame1 = cam.read_oldest_image()
        with tWait:
            cam.wait_for_frame()
            frame2 = cam.read_oldest_image()
    cam.stop_acquisition()
print(Timer.timers.mean(tKey))
print(Timer.timers.stdev(tKey))
