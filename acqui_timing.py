#%%
import pylablib as pll
import matplotlib.pyplot as plt
import os
from codetiming import Timer
os.environ["PYLON_CAMEMU"] = "1" # use one emu cam
pll.par["devices/dlls/basler_pylon"] = r"C:\Program Files\Basler\pylon 8\Runtime\x64\PylonC_v9.dll"
from pylablib.devices import Basler

#%%
N = 100
t = Timer()
with Basler.BaslerPylonCamera() as cam:
    # cam.set_roi(0,128,0,128)
    cam.set_frame_period(0)
    print(cam.get_frame_timings())
    with t:
        for _ in range(N):
            image = cam.grab(1)

print(f"{t.last*1e3/N} ms per grab")
# %%
N = 100
t = Timer()
with Basler.BaslerPylonCamera() as cam:
    cam.start_acquisition(mode="sequence", nframes=100)
    # cam.set_roi(0,128,0,128)
    with t:
        for _ in range(N):
            cam.wait_for_frame()
            frame = cam.read_oldest_image()
    cam.stop_acquisition()
print(f"{t.last*1e3/N} ms per grab")
#%%
N = 100
t = Timer()
with Basler.BaslerPylonCamera() as cam:
    # cam.set_roi(0,128,0,128)
    cam.setup_acquisition(mode="sequence", nframes=100)
    with t:
        for _ in range(N):
            cam.start_acquisition()
            cam.wait_for_frame()
            frame = cam.read_oldest_image()
            cam.stop_acquisition()
print(f"{t.last*1e3/N} ms per grab")