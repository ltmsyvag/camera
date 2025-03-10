#%%
import threading
import time
acquiring = True

def acquisition_loop():
    global acquiring
    try:
        while acquiring:
            print("blah"); time.sleep(1)
    finally:
        print("done!")

acq_thread = threading.Thread(target = acquisition_loop)
acq_thread.start()

time.sleep(5)
acquiring=False
acq_thread.join()