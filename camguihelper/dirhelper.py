"""
用于统一存放
├-- session_data_root/
                    ├-- session_frames/ # data root
                    |    ├-- 2025/
                    |    |     ├-- 一月/
                    |    |     |     ├-- 01/
                    |    |     |     └-- 02/
                    |    |     |          ├-- 0001/
                    |    |     |          └-- 0002/
                    |    |     |               ├-- 0002_0.tiff
                    |    |     |               └-- 0002_1.tiff
                    |    |     └-- 二月/
                    |    |           ├-- 01/
                    |    |           └-- 02/
                    |    |                ├-- 0001/
                    |    |                └-- 0002/
                    |    └-- 2026/
                    └-- camgui_params/
                         ├-- 2025/
                         |     ├-- 一月/
                         |     |     ├-- 01/
                         |     |     └-- 02/
                         |     |          ├-- 0001.json
                         |     |          └-- 0002.json
                         |     └-- 二月/
                         |           ├-- 01/
                         |           └-- 02/
                         |                ├-- 0001.json
                         |                └-- 0002.json
                         └-- 2026/
"""
from pathlib import Path
import os
import datetime
import dearpygui.dearpygui as dpg

class MyPath(Path):
    def is_readable(self):
        return os.access(self, os.R_OK)
    def is_writable(self):
        return os.access(self, os.W_OK)
    def is_executable(self):
        return os.access(self, os.X_OK)

session_data_root = MyPath("session_data_root")
session_frames_root = session_data_root / "session_frames"
# 未来还会有一个 session_params_root, 用于存放 session manager 面板数据, 只有 session_frames_root 和 session_params_root 可以用 session 这个前缀, 其他任何仪器软件保存的面板数据都不应该以 session 做前缀
camgui_params_root = session_data_root / "camgui_params"
month_dict = {
            "01" : "一月",
            "02" : "二月",
            "03" : "三月",
            "04" : "四月",
            "05" : "五月",
            "06" : "六月",
            "07" : "七月",
            "08" : "八月",
            "09" : "九月",
            "10" : "十月",
            "11" : "十一月",
            "12" : "十二月"}

def mkdir_session_frames():
        """
        未来的 SESSION MANAGER 函数
        有两种 dir 被称为 session dir (camgui 创建的 dir 不配被叫做 session dir):
        1. frames dir, 保存每个 session 的 data
        2. parameters dir, 保存每个 session 的 session manager 面板数据
        本函数创建新的 session frames dir, 最终本函数的功能应该由 session manager 代码完成
        """
        from .core import push_log, UserInterrupt # import inside this func to avoid circular importation error (happens when this import is put on top of .py). 这个 lazy loading 在这里是正当的权宜之计, 因为最终 make session dir 的是 session manager, 而不是 camgui, make session dir 失败时, 报错是在 session manager 中报错, 不是在 camgui 中, 因此最终 make session dir 时完全用不到 camgui 的 push_log 函数
        if session_frames_root.is_dir() and session_frames_root.is_writable(): # `is_dir` 保证 dir 存在且是 dir (不是文件名), `is_writable` 保证 dir 可写. 这个 check 用于在 Z 盘丢失 (或者换新 Z 盘的时候) 给用户一个信息, 要求用户重新连接 Z 盘, 或者 explicitly 设置好空的 frames root
            year_str, month_str, day_str = datetime.date.today().strftime("%Y-%m-%d").split("-")
            month_str = month_dict[month_str] # convert to chinese
            dpath_day = session_frames_root / year_str / month_str / day_str
            if dpath_day.exists():
                lst_ses_dpaths = list(dpath_day.iterdir())
                if lst_ses_dpaths: # 防止 day dir 是空的, 这种情况只可能发生在用户手动清空 day dir 的时候
                    final_ses_dpath = lst_ses_dpaths[-1]
                    new_ses_num = int(str(final_ses_dpath)[-4:]) + 1 
                    new_ses_str = str(new_ses_num).zfill(4)
                else:
                    new_ses_str = "0001"
            else:
                new_ses_str = "0001"
            dpath = dpath_day / new_ses_str
            dpath.mkdir(parents=True)
            select_all_fpath = dpath / "_select_all"
            select_all_fpath.touch() # create empty _select_all file for selecting all tiffs in file dialog
        else:
            push_log(f"找不到用于存放帧数据的文件夹 {str(session_frames_root)}", is_error=True)
            raise UserInterrupt

