#%%
import pylablib as pll
from pylablib.devices import DCAM
from codetiming import Timer
import matplotlib.pyplot as plt
# tSnap = Timer("tSnap", logger=None)
tKey = "tWait9.9hz"
tWait = Timer(tKey, logger=None)

with DCAM.DCAMCamera() as cam:
    # print(cam.get_defect_correct_mode())
    # cam.set_frame_format("chunks")
    # cam.set_trigger_mode("software")
    cam.set_trigger_mode("ext")
    cam.set_exposure(0.1) # default 0.0082944
    cam.set_roi(1352,1352+240,948,948+240) # full region (2304, 4096)
    # cam.send_software_trigger()
    # frame1 = cam.snap()
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

fig, axs = plt.subplots(ncols=2, figsize = (8,4.8))
axs[0].imshow(frame1,aspect='auto')
axs[1].imshow(frame2,aspect='auto')

# %%
