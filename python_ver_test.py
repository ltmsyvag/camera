#%% 如果 python 版本太老， 则 camgui 启动报错，等价于下面的 test 代码无法无法运行
import os
from pathlib import Path
class MyPath(Path):
    def is_readable(self):
        return os.access(self, os.R_OK)
    def is_writable(self):
        return os.access(self, os.W_OK)
    def is_executable(self):
        return os.access(self, os.X_OK)
    
#%%
session_data_root = MyPath('Z:/实验数据/session_data_root')
# %%
