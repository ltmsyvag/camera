#%% 
from pylablib.devices import DCAM
import matplotlib.pyplot as plt
import threading
import time
myRoi = 1352,1352+240,948,948+240
expo = 0

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

eventKeepAcquiring = threading.Event()
def acq_loop(cam: DCAM.DCAMCamera, event: threading.Event)-> None:
    while event.is_set():
        try:
            cam.wait_for_frame(timeout=1)
        except DCAM.DCAMTimeoutError:
            print("timeout")
            continue
        thisFrame = cam.read_oldest_image()
        _, ax = plt.subplots()
        ax.imshow(thisFrame)

threadAcq = threading.Thread(target=acq_loop, args=(cam, eventKeepAcquiring))

eventKeepAcquiring.set()
threadAcq.start()
print("start sleeping")
time.sleep(10)
eventKeepAcquiring.clear()
print("done sleeping")
threadAcq.join()
cam.stop_acquisition()
cam.close()

print("====THE END====")
# %%
