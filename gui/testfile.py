#%%
from guihelplib import _myRandFrame
from codetiming import Timer
import numpy as np
import tifffile
from guihelplib import FrameStack

frameStack = FrameStack()

with Timer():
    frameStack = FrameStack(_myRandFrame(240,240,65535).astype(int) for _ in range(10))
frameStack.getAvgFrame()

#%%
with Timer():
    # frame = frame.astype(int)
    intFrameStack = [(frame.astype(int)-200)*0.1/0.9 for frame in frameStack]
# print(sum(intFrameStack))
frame = frameStack[0].astype(np.uint16)

with Timer(text = "do nothing takes {} s"):
    pass
with Timer(text = "same type conversion takes {} s"):
    frame.astype(np.uint16)
with Timer(text = "int conversion takes {} s"):
    frame = frame.astype(float)
# tifffile.imsave("frame.tiff",frame.astype(np.uint16))