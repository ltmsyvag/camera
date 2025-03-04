#%%
import time
try:
    while True:
        print(time.time())
        time.sleep(1)
except KeyboardInterrupt: # click the Interrupt button of python interactive window
    print("end")