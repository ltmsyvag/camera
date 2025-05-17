#%%
from pylablib.devices import DCAM
cam = DCAM.DCAMCamera()
cam.open()
print("cam opened")
cam.close()
print("cam closed")
cam2 = DCAM.DCAMCamera()
cam2.open()
print("cam opened")
cam2.close()
print("cam closed")

print(id(cam), id(cam2))