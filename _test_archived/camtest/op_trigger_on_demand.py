#%% playing with master pulse and output trigger, not successful yet.
from pylablib.devices import DCAM
import matplotlib.pyplot as plt
import time
import itertools
binaryCycle = itertools.cycle([False,True])
def closeCamAndSay(str):
    cam.stop_acquisition()
    cam.close()
    print(str)

cam = DCAM.DCAMCamera()
if cam.is_opened(): cam.close()
cam.open(); print("cam opened")
cam.set_trigger_mode("master_pulse")
cam.cav["master_pulse_mode"] = 1 # *1 continuous; 2 start; 3 burst
cam.cav["master_pulse_trigger_source"] = 2 # *1 external; 2 software
# cam.cav["trigger_polarity"] = 2
# cam.cav["output_trigger_source[0]"] = 6 # 2 readout end; 3 vsync; 6 trigger
# # cam.cav["output_trigger_active[0]"] = 1 # 1 edge
# cam.cav["output_trigger_polarity[0]"] = 2 # 1 negative; 2 positive
# cam.cav["output_trigger_kind[0]"] = 3 # 1 low； 2 exposure; 3 programmable; 4 trigger ready; 5 high; 6 anyrow exposure

# cam.cav["output_trigger_period[0]"] = 0.01

cam.set_exposure(0.006) # default 0.0082944
cam.set_roi(1352,1352+240,948,948+240) # full region (2304, 4096)
cam.start_acquisition(mode="sequence")
try:
    while True:
        cam.wait_for_frame(timeout=None)
        frame = cam.read_oldest_image()
        cam.send_software_trigger()
        nFramesTaken = cam.get_device_variable("acquired_frames")
        if not nFramesTaken%10: print(nFramesTaken)
except KeyboardInterrupt:
    closeCamAndSay("======THE END=======")

# %%
