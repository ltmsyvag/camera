#%%
import tifffile
from camguihelper import MyPath
path = MyPath("20by20 images")
fnames = list(path.glob("*.tif"))
flist = [tifffile.imread(e) for e in fnames]
# frame_deck = Framedeck(flist)
# myarr = flist[0].astype(float)