#%%
from pylablib.devices import DCAM
import matplotlib.pyplot as plt
from codetiming import Timer

frameList = []
with DCAM.DCAMCamera() as cam:
    cam.cav["sensor_mode"] = 18 # 1 area; 12 progressive; 18 photon number resolving
    for exp in (0,0.01,0.1,1):
        cam.set_exposure(exp)
        frameList.append(cam.snap())


for frame in frameList:
    _min, _max, _mean, _std = frame.min(), frame.max(), frame.mean(), frame.std()
    fig, ax = plt.subplots()
    im = ax.imshow(frame, vmin=_min, vmax=_max)
    fig.colorbar(im)
    ax.set_title(f"min num {_min}, max num {_max}, \nmean num {_mean:.2f}±{_std:.2f}")


# %%
