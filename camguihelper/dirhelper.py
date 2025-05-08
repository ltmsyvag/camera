"""
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
from .core import push_log

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
        有两种 dir 被称为 session dir (camgui 创建的 dir 不配被叫做 session dir):
        1. frames dir, 保存每个 session 的 data
        2. parameters dir, 保存每个 session 的 session manager 面板数据
        本函数创建新的 frames dir
        """
        if session_frames_root.is_dir() and session_frames_root.is_writable(): # `is_dir` 保证 dir 存在且是 dir (不是文件名), `is_writable` 保证 dir 可写. 这个 check 防止
            now = datetime.now()
            year_str, month_str, day_str = now.strftime("%Y-%m-%d").split("-")
            month_str = month_dict[month_str] # convert to chinese
        else:
            push_log(f"找不到用于存放帧数据的文件夹 {str(session_frames_root)}", is_error=True)
            raise Exception # 人工阻止后续程序运行. 因为本函数是一个 cb, cb 是单独的线程, 所以 gui 不会崩