#%%
from matplotlib import font_manager

fonts = set(f.name for f in font_manager.fontManager.ttflist)
sList = sorted(fonts)
for e in sList: print(e)
#%%
from matplotlib import font_manager

# Get list of all fonts
for f in font_manager.findSystemFonts(fontpaths=None, fontext="ttf"):
    if "PingFang" in f:
        print(f)