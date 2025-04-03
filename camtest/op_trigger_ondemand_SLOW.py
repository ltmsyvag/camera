#%%
from pylablib.devices import DCAM
from codetiming import Timer
import time
tUD = Timer("updown", logger=None)
tU = Timer("up", logger=None)
tD = Timer("down", logger=None)
def closeCamAndSay(str):
    cam.stop_acquisition()
    cam.close()
    print(str)

with DCAM.DCAMCamera() as cam:
    print("cam opened")
    cam.set_trigger_mode("ext")
    cam.cav["output_trigger_kind[0]"] = 1
    try:
        while True:
            with tUD:
                with tU: cam.cav["output_trigger_kind[0]"] = 5
                with tD: cam.cav["output_trigger_kind[0]"] = 1
    except KeyboardInterrupt:
        closeCamAndSay("===========THE END")

print(Timer.timers.mean("updown"))
print(Timer.timers.stdev("updown"))
print(Timer.timers.mean("up"))
print(Timer.timers.stdev("up"))
print(Timer.timers.mean("down"))
print(Timer.timers.stdev("down"))
    # cam.cav["output_trigger_kind[0]"] = 5 # 1 low； 2 exposure; 3 programmable; 4 trigger ready; 5 high; 6 anyrow exposure
    # input("press anything to resume...")
    # closeCamAndSay("===========THE END")
    
    
    # cam.cav["trigger_polarity"] = 2
    # cam.cav["output_trigger_source[0]"] = 2 # 2 readout end; 3 vsync; 6 trigger
    # # cam.cav["output_trigger_active[0]"] = 1 # 1 edge
    # cam.cav["output_trigger_polarity[0]"] = 2 # 1 negative; 2 positive
    # cam.cav["output_trigger_kind[0]"] = 3 # 1 low； 2 exposure; 3 programmable; 4 trigger ready; 5 high; 6 anyrow exposure

    # cam.cav["output_trigger_period[0]"] = 0.01


# %%
