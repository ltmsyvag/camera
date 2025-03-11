#%% 
from pylablib.devices import DCAM
import matplotlib.pyplot as plt
myRoi = 1352,1352+240,948,948+240
expo = 0
import time

cam = DCAM.DCAMCamera()
if cam.is_opened(): cam.close()

cam.open()
cam.set_trigger_mode("ext")
cam.set_exposure(expo) # default 0.0082944
cam.set_roi(*myRoi) # full region (2304, 4096)
cam.setup_acquisition(mode="snap", nframes=100)
print("waiting for trigger")

id = 0
cam.start_acquisition()
try:
    while True:
        try: 
            cam.wait_for_frame(timeout=1)
            print("still waiting")
        except DCAM.DCAMTimeoutError:
            print("timeout")
            continue
        thisFrame = cam.read_oldest_image()
        fig, ax = plt.subplots()
        ax.imshow(thisFrame)
        plt.show()
except KeyboardInterrupt:
    cam.stop_acquisition()
    cam.close()
    print("=======THE END=====")


# %%
