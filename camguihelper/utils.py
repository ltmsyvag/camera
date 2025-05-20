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
import re

class UserInterrupt(Exception):
    """
    打断 callback 所用的 exception
    """
    pass
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

def _mk_save_tree_from_root_to_day(root_dir : MyPath) -> MyPath:
    """
    给定一个 root_dir, 创建并返回当前日期的 save tree
    e.g. 'root/2025/五月/20/'
    如果 root_dir 不存在, 抛出异常
    """
    if root_dir.is_dir() and root_dir.is_writable(): # `is_dir` 保证 dir 存在且是 dir (不是文件名), `is_writable` 保证 dir 可写. 这个 check 用于在 Z 盘丢失 (或者换新 Z 盘的时候) 给用户一个信息, 要求用户重新连接 Z 盘, 或者 explicitly 设置好空的 frames root
        year_str, month_str, day_str = datetime.date.today().strftime("%Y-%m-%d").split("-")
        month_str = month_dict[month_str] # convert to chinese
        dpath_day = root_dir / year_str / month_str / day_str
        return dpath_day
    else: 
        UserInterrupt

def _find_newest_daypath_in_save_tree(root_dir : MyPath)-> MyPath:
    """
    在某一个 root 下找到最新的 day path 并返回, 
    e.g. 'root/2025/五月/20/'
    按照最新年, 月, 日的次序找到的 save tree 不完整
    比如只有 root/2025/五月/ (空月份文件夹) 或者 root/2025/ (空年份文件夹)
    则抛出 UserInterrupt.
    因为自动创建的 save tree 不会出现这种缺失, 因此需要 explicitly 让用户知道有奇怪的情况
    """
    ### 开始 redundant check
    if not root_dir.exists():
        # push_log("没有找到 session dir, 请检查 Z 盘是否连接", is_error=True)
        raise UserInterrupt("没有找到 session dir, 请检查 Z 盘是否连接")
    if not root_dir.is_writable():
        # push_log("目标路径不可写", is_error=True)
        raise UserInterrupt("目标路径不可写")
    ### find latest year dpath
    year_pattern = r"2\d{3}$" # A105 不可能存活到 3000 年
    def _year_sorter(dpath: MyPath):
        if re.match(year_pattern, dpath.name):
            return int(dpath.name)
        else:
            return -1 # 其他我不关心的东西都排最前面
    lst_year_dirs = sorted(list(root_dir.iterdir()), key= _year_sorter)
    if not lst_year_dirs:
        # push_log("保存失败: 帧数据路径是空的", is_error=True)
        raise UserInterrupt("异常: 帧数据路径是空的")
    dpath_year = lst_year_dirs[-1]
    if not re.match(year_pattern, dpath_year.name):
        # push_log("保存失败: 帧数据路径中没有任何文件夹", is_error=True)
        raise UserInterrupt("异常: 帧数据路径中没有任何文件夹")
    ### find latest month dpath
    month_sort_dict = dict()
    for key, val in month_dict.items():
        month_sort_dict[val] = int(key)
    def _month_sorter(dpath: MyPath):
        if dpath.name in month_sort_dict:
            return month_sort_dict[dpath.name]
        else:
            return -1
    lst_month_dirs = sorted(list(dpath_year.iterdir()), key= _month_sorter)
    if not lst_month_dirs:
        # push_log("保存失败: 当年文件夹是空的", is_error=True)
        raise UserInterrupt("异常: 当年文件夹是空的")
    dpath_month = lst_month_dirs[-1]
    if dpath_month.name not in month_sort_dict:
        # push_log("保存失败: 当年文件夹中没有任何月份文件夹", is_error=True)
        raise UserInterrupt("异常: 当年文件夹中没有任何月份文件夹")
    ### find latest day dpath
    day_pattern = r"^\d{2}$"
    def _day_sorter(dpath: MyPath):
        if re.match(day_pattern, dpath.name):
            return int(dpath.name)
        else:
            return -1
    lst_day_dirs = sorted(list(dpath_month.iterdir()), key= _day_sorter)
    if not lst_day_dirs:
        # push_log("保存失败: 当月文件夹是空的", is_error=True)
        raise UserInterrupt("异常: 当月文件夹是空的")
    dpath_day = lst_day_dirs[-1]
    if not re.match(day_pattern, dpath_day.name):
        # push_log("保存失败: 当月文件夹中没有任何日期文件夹", is_error=True)
        raise UserInterrupt("异常: 当月文件夹中没有任何日期文件夹")
    return dpath_day

def find_latest_sesframes_folder() ->MyPath:
    dpath_day = _find_newest_daypath_in_save_tree(session_frames_root)
    ### find latest session dpath
    session_pattern = r"^\d{4}$"
    def _session_sorter(dpath: MyPath):
        if re.match(session_pattern, dpath.name):
            return int(dpath.name)
        else:
            return -1
    lst_ses_dirs = sorted(list(dpath_day.iterdir()), key= _session_sorter)
    if not lst_ses_dirs:
        # push_log("异常: 帧数据 save tree 中最新日期的文件夹是空的", is_error=True)
        raise UserInterrupt("异常: 帧数据 save tree 中最新日期的文件夹是空的")
    dpath_ses = lst_ses_dirs[-1]
    if not re.match(session_pattern, dpath_ses.name):
        # push_log("异常: 帧数据 save tree 中最新日期的文件夹中没有任何 session 编号文件夹", is_error=True)
        raise UserInterrupt("异常: 帧数据 save tree 中最新日期的文件夹中没有任何 session 编号文件夹")
    return dpath_ses

def mkdir_session_frames() -> str:
    """
    未来的 SESSION MANAGER 函数
    有两种 dir 被称为 session dir (camgui 创建的 dir 不配被叫做 session dir):
    1. frames dir, 保存每个 session 的 data
    2. parameters dir, 保存每个 session 的 session manager 面板数据
    本函数创建新的 session frames dir, 最终本函数的功能应该由 session manager 代码完成
    """
    from .core import push_exception, push_log # import inside this func to avoid circular importation error (happens when this import is put on top of .py). 这个 lazy loading 在这里是正当的权宜之计, 因为最终 make session dir 的是 session manager, 而不是 camgui, make session dir 失败时, 报错是在 session manager 中报错, 不是在 camgui 中, 因此最终 make session dir 时完全用不到 camgui 的 push_log 函数
    dpath_day = _mk_save_tree_from_root_to_day(session_frames_root)
    # if session_frames_root.is_dir() and session_frames_root.is_writable(): # `is_dir` 保证 dir 存在且是 dir (不是文件名), `is_writable` 保证 dir 可写. 这个 check 用于在 Z 盘丢失 (或者换新 Z 盘的时候) 给用户一个信息, 要求用户重新连接 Z 盘, 或者 explicitly 设置好空的 frames root
    #     year_str, month_str, day_str = datetime.date.today().strftime("%Y-%m-%d").split("-")
    #     month_str = month_dict[month_str] # convert to chinese
    #     dpath_day = session_frames_root / year_str / month_str / day_str
    extra_confirm = False
    if dpath_day.exists():
        try:
            dpath_newest_ses = find_latest_sesframes_folder()
            ses_num_latest = int(dpath_newest_ses.name)
            new_ses_str = str(ses_num_latest + 1).zfill(4)
        except UserInterrupt:
            push_exception('创建 session 文件夹时发现异常')
            new_ses_str = '0001'
            extra_confirm = True
        # lst_ses_dpaths = list(dpath_day.iterdir())
        # if lst_ses_dpaths: # 防止 day dir 是空的, 这种情况只可能发生在用户手动清空 day dir 的时候
        #     final_ses_dpath = lst_ses_dpaths[-1]
        #     new_ses_num = int(str(final_ses_dpath)[-4:]) + 1 
        #     new_ses_str = str(new_ses_num).zfill(4)
        # else:
        #     new_ses_str = "0001"
    else:
        new_ses_str = '0001'

    dpath = dpath_day / new_ses_str
    
    dpath.mkdir(parents=True)
    select_all_fpath = dpath / '_select_all'
    select_all_fpath.touch() # create empty _select_all file for selecting all tiffs in file dialog
    if extra_confirm:
        push_log('虽然有异常, 但是 session 文件夹创建依然成功', is_good = True)
    return new_ses_str
    # else:
    #     # push_log(f"找不到用于存放帧数据的文件夹 {str(session_frames_root)}", is_error=True)
    #     raise UserInterrupt