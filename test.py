#%%
from pathlib import Path
dpath = Path("session_data_root/session_frames/2025/五月/08/0006")
flist = [e for e in dpath.iterdir() if e.suffix in [".ico", ".tiff"]]
print(flist)
# %%
