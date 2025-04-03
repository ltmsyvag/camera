#%% open 应用。接收两个 trigger 后，输出两张图
from pylablib.devices import DCAM
import matplotlib.pyplot as plt

cam = DCAM.DCAMCamera()
if cam.is_opened(): cam.close()
cam.open()
cam.set_trigger_mode("ext")
cam.set_exposure(0.1) # default 0.0082944
cam.set_roi(1352,1352+240,948,948+240) # full region (2304, 4096)
cam.setup_acquisition(mode="snap", nframes=100)
print("waiting for trigger")

cam.start_acquisition()
cam.wait_for_frame(timeout=None)
frame1 = cam.read_oldest_image()

cam.wait_for_frame()
frame2 = cam.read_oldest_image()
cam.stop_acquisition()
cam.close()


fig, axs = plt.subplots(ncols=2, figsize = (8,4.8))
axs[0].imshow(frame1,aspect='auto')
axs[1].imshow(frame2,aspect='auto')