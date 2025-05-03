#%%
import tifffile
# from .core import MyPath
from pathlib import Path

path = Path("20by20 images") # somehow this is the repo root dir no matter where the current py file is placed
fnames = list(path.glob("*.tif"))
frame_list = [tifffile.imread(e) for e in fnames]
