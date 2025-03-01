#%%
import pylablib as pll
from pylablib.devices import DCAM
from codetiming import Timer
import matplotlib.pyplot as plt
with DCAM.DCAMCamera() as cam:

    # print(cam.setup_ext_trigger())
    # print(cam.set_trigger_mode("ext"))
    # print(cam.get_ext_trigger_parameters())
    print(cam.attributes)
    print("===settings==")
    for e in cam._device_vars["settings"].items(): print(e[0], "||", cam.get_device_variable(e[0]))
    print("===status==")
    for e in cam._device_vars["status"].items(): print(e[0], "||", cam.get_device_variable(e[0]))
    print("===info==")
    for e in cam._device_vars["info"].items(): print(e[0], "||", cam.get_device_variable(e[0]))