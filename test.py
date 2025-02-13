#%%
import pylablib as pll
pll.par["devices/dlls/basler_pylon"] = r"C:\Program Files\Basler\pylon 8\Runtime\x64\PylonC_v9.dll"
from pylablib.devices import Basler
# cameras = Basler.list_cameras()
cam = Basler.BaslerPylonCamera()

# %%
