#%%
import pylablib as pll
import matplotlib.pyplot as plt
import os
os.environ["PYLON_CAMEMU"] = "1" # use one emu cam
pll.par["devices/dlls/basler_pylon"] = r"C:\Program Files\Basler\pylon 8\Runtime\x64\PylonC_v9.dll"
from pylablib.devices import Basler
cameras = Basler.list_cameras()
print(cameras) # 查看相机 metadata
with Basler.BaslerPylonCamera() as cam:
    cam.set_roi(0,128,0,128)
    images = cam.grab(10)
    print(
        cam.get_frame_timings(), # 查看 frame period
        cam.get_detector_size(), # 查看感光单元像素
        cam.get_all_attribute_values(), # 查看所有特性
        cam.ca["ExposureTime"], # 查看所有特性
        sep='\n==========\n'
        ) 
    # for i in range(10):
    #     fig, ax = plt.subplots()
    #     ax.imshow(images[i], cmap='gray')
# %%
