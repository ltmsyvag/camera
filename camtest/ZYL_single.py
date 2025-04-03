#%% 
from pylablib.devices import DCAM
import matplotlib.pyplot as plt
myRoi = 1352,1352+240,948,948+240
expo = 0
nFrames = 3 # number of frames to acquire per session



cam = DCAM.DCAMCamera()
if cam.is_opened(): cam.close()

cam.open()
cam.set_trigger_mode("ext")
cam.set_exposure(expo) # default 0.0082944
cam.set_roi(*myRoi) # full region (2304, 4096)
cam.setup_acquisition(mode="snap", nframes=100)
lstFrames = []
print("waiting for trigger")


cam.start_acquisition()
for _ in range(nFrames):
    cam.wait_for_frame(timeout=None)
    thisFrame = cam.read_oldest_image()
    lstFrames.append(thisFrame)
cam.stop_acquisition()
cam.close()


nCols = 2 # number of columns of output figure
nRows=nFrames//nCols + 1 if nFrames%nCols else 0
fig, axs = plt.subplots(
    ncols=nCols,
    nrows=nRows,
    figsize = (10,5*nRows))
axs = axs.flatten()
for id, (ax, frame) in enumerate(zip(axs, lstFrames)):
    ax.imshow(frame,aspect="auto")
    ax.set_title(f"frame {id+1}")

# %%
