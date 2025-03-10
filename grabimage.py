#%%
from pylablib.devices import DCAM
import matplotlib.pyplot as plt

frameList = []
with DCAM.DCAMCamera() as cam:
    for exp in (0,0.01,0.1,1):
        cam.set_exposure(exp)
        frameList.append(cam.grab(1)[0])


for frame in frameList:
    fig, ax = plt.subplots()
    ax.imshow(frame)
    ax.set_title(f"min num {frame.min()}, max num {frame.max()}")

