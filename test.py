#%%
from camguihelper import MyPath
dpath = MyPath("")
dpath = dpath/ "frames"
print(
    dpath.exists()
)