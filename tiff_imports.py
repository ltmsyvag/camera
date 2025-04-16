#%%
import tifffile
from camguihelper import MyPath
path = MyPath("20by20 images")
fnames = list(path.glob("*.tif"))
flist = [tifffile.imread(e) for e in fnames]
# frame_stack = FrameStack(flist)
# myarr = flist[0].astype(float)