#%% simple implementation
import threading
import time
keepTalking = True

def blah_loop():
    try:
        while keepTalking:
            print("blah"); time.sleep(1)
    finally:
        print("done!")

talk_thread = threading.Thread(target = blah_loop)
talk_thread.start()

time.sleep(5)
keepTalking=False
talk_thread.join()
#%% cleaner implementation
event_keepTalking = threading.Event()
def blah_loop():
    try:
        while event_keepTalking.is_set():
            print("blah"); time.sleep(1)
    finally:
        print("done!")
talk_thread = threading.Thread(target = blah_loop)
event_keepTalking.set()
talk_thread.start()

time.sleep(5)
event_keepTalking.clear()
talk_thread.join()