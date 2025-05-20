"""
camgui 相关的帮助函数
"""
#%%
camgui_ver = '1.3-pre'
from itertools import cycle
from collections import namedtuple
import multiprocessing.connection
DupeMap = namedtuple(typename='DupeMap', # class for useful dpg items in a dupe heatmap window
                        field_names=['yAx', 'inputInt', 'radioBtn', 'cBox'])

import json
import traceback
import multiprocessing
import queue
import time
import copy
import numpy.typing as npt
from typing import List, Dict, Sequence
import re
from deprecated import deprecated
import math
from datetime import datetime
from pylablib.devices import DCAM
import numpy as np
import threading
import colorsys
import tifffile
from .utils import MyPath, UserInterrupt, camgui_params_root, _mk_save_tree_from_root_to_day, find_latest_sesframes_folder, _find_newest_daypath_in_save_tree
import dearpygui.dearpygui as dpg
import platform, uuid
# system = platform.system()
# if (system == "Windows") and (hex(uuid.getnode()) != '0xf4ce2305b4c7'): # code is A402 computer
import spcm
from AWG_module.no_with_func import DDSRampController
from AWG_module.unified import feed_AWG

class FrameDeck(list):
    """
    class of a special list with my own methods for manipulating the frames it stores
    """

    def __init__(self, 
                #  frames_root_str: str=str(frames_root) #默认使用 dirhelper 中定义的 frames root, 但允许 camgui.py 代码中用其他路径 override, 以便测试
                 *args, **kwargs):
        """
        将状态变量作为 instance attr 初始化
        好处(相对于 class attr 来说)是在不重启 kernel, 只重启 camgui.py 的情况下,
        frame_deck 的状态不会保留上一次启动的记忆
        """
        super().__init__(*args, **kwargs) # make sure I do not override the parent dunder init
        self.cid: int | None = None # current heatmap's id in deck
        self.float_deck: List[npt.NDArray[np.floating]] = [] # gui 中的操作需要 float frame, 因此与 list (int deck) 对应, 要有一个 float deck
        self.frame_avg: npt.NDArray[np.floating] | None = None
        self.lst_dupe_maps : List[DupeMap] = [] # 保存 duplicated heatmaps window 中的 item tuple
        self.seslabel_deck: List[str] = []
    def memory_report(self) -> str:
        len_deck = len(self)
        if len_deck>0:
            mbsize_int_frames = sum([frame.nbytes for frame in self])/(1024**2)
            mbsize_float_frames = sum([frame.nbytes for frame in self])/(1024**2)
            size = mbsize_int_frames + mbsize_float_frames
        else:
            size = 0
        return  f"内存: {len_deck} 帧 ({size:.2f} MB)"
    # @deprecated
    # def memory_report_(self) -> str:
    #     len_deck = len(self)
    #     if len_deck > 0:
    #         mbsize_1_int_frame = self[0].nbytes/ (1024**2)
    #         mbsize_1_float_frame = self.float_deck[0].nbytes/ (1024**2)
    #     else:
    #         mbsize_1_int_frame = mbsize_1_float_frame = 0
    #     return f"内存: {len_deck} 帧 ({(mbsize_1_float_frame+mbsize_1_int_frame)*len_deck:.2f} MB)"
    @staticmethod
    def _make_savename_stub():
        """
        如果想保存的文件时间是
        "C:\\Users\\username\\Desktop\\2023-10-01-12-00-00_id.tiff",
        那么在 Desktop 存在并可写入, 且 frame deck 非空的情况下, 返回字符串形式的 stub
        "C:\\Users\\username\\Desktop\\2023-10-01-12-00-00"
        """
        dpath = MyPath(dpg.get_value("save path input field"))
        dpath.mkdir(parents=True, exist_ok=True)
        if dpath.is_dir() and dpath.is_writable():
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            fpath_stub = str(dpath / timestamp)
            return fpath_stub
        else:
            push_log("输入的路径有问题", is_error=True)
            raise UserInterrupt # 人工阻止后续程序运行. 因为 cb 是单独的线程, 所以 gui 不会崩
    def append(self, frame: np.ndarray):
        """
        append a new frame to int & float decks
        同时执行: 
        - cid update
        - 平均 heatmap 计算
        - counts display update
        - cid indicator updates
        append 现在貌似是为 frame_deck 添加 frame 的唯一入口, let's keep it that way
        """
        # print(frame.dtype)
        assert frame.dtype == np.uint16, "frame should be uint16, something's off?!"

        super().append(frame)
        self.float_deck.append(frame.astype(float))
        self.cid = len(self) - 1
        # self.frame_avg = sum(self.float_deck) / len(self.float_deck)
        self.frame_avg = np.mean(self.float_deck, axis=0)
        dpg.set_value("frame deck display", self.memory_report())
        dpg.set_item_label("cid indicator", f"{self.cid}")
    def save_deck(self)->None:
        """
        保存全部 frames, 并 push 成功/失败 message
        """
        fpath_stub = self._make_savename_stub()
        if self:
            for i, frame in enumerate(self):
                fpath = fpath_stub + f"_{i}.tif"
                try:
                    tifffile.imwrite(fpath, frame)
                except Exception:
                    push_exception(f"帧 #{i} 保存失败.")
                
            push_log("全部帧保存成功", is_good=True)
        else:
            push_log("内存中没有任何帧", is_error=True)
    def save_cid_frame(self)->None:
        """
        保存 cid 指向的 frame, 并 push 成功/失败 message
        """
        # with Timer():
        fpath_stub = self._make_savename_stub()
        if self.cid: # 当前 cid 不是 None, 则说明 deck 非空
            fpath = fpath_stub + f"_{self.cid}.tif"
            try:
                tifffile.imwrite(fpath, self[self.cid])
            except Exception:
                push_exception("当前帧保存失败")
                return
            push_log("当前帧保存成功", is_good=True)
        else:
            push_log("内存中没有任何帧", is_error=True)
    def _find_lastest_sesframes_folder_and_save_frame(self)-> str:
        # ### 开始 redundant check
        # if not session_frames_root.exists():
        #     push_log("没有找到 session dir, 请检查 Z 盘是否连接", is_error=True)
        #     raise UserInterrupt
        # if not session_frames_root.is_writable():
        #     push_log("目标路径不可写", is_error=True)
        #     raise UserInterrupt
        # ### find latest year dpath
        # year_pattern = r"2\d{3}$" # A105 不可能存活到 3000 年
        # def _year_sorter(dpath: MyPath):
        #     if re.match(year_pattern, dpath.name):
        #         return int(dpath.name)
        #     else:
        #         return -1 # 其他我不关心的东西都排最前面
        # lst_year_dirs = sorted(list(session_frames_root.iterdir()), key= _year_sorter)
        # if not lst_year_dirs:
        #     push_log("保存失败: 帧数据路径是空的", is_error=True)
        #     raise UserInterrupt
        # dpath_year = lst_year_dirs[-1]
        # if not re.match(year_pattern, dpath_year.name):
        #     push_log("保存失败: 帧数据路径中没有任何文件夹", is_error=True)
        #     raise UserInterrupt
        # ### find latest month dpath
        # month_sort_dict = dict()
        # for key, val in month_dict.items():
        #     month_sort_dict[val] = int(key)
        # def _month_sorter(dpath: MyPath):
        #     if dpath.name in month_sort_dict:
        #         return month_sort_dict[dpath.name]
        #     else:
        #         return -1
        # lst_month_dirs = sorted(list(dpath_year.iterdir()), key= _month_sorter)
        # if not lst_month_dirs:
        #     push_log("保存失败: 当年文件夹是空的", is_error=True)
        #     raise UserInterrupt
        # dpath_month = lst_month_dirs[-1]
        # if dpath_month.name not in month_sort_dict:
        #     push_log("保存失败: 当年文件夹中没有任何月份文件夹", is_error=True)
        #     raise UserInterrupt
        # ### find latest day dpath
        # day_pattern = r"^\d{2}$"
        # def _day_sorter(dpath: MyPath):
        #     if re.match(day_pattern, dpath.name):
        #         return int(dpath.name)
        #     else:
        #         return -1
        # lst_day_dirs = sorted(list(dpath_month.iterdir()), key= _day_sorter)
        # if not lst_day_dirs:
        #     push_log("保存失败: 当月文件夹是空的", is_error=True)
        #     raise UserInterrupt
        # dpath_day = lst_day_dirs[-1]
        # if not re.match(day_pattern, dpath_day.name):
        #     push_log("保存失败: 当月文件夹中没有任何日期文件夹", is_error=True)
        #     raise UserInterrupt
        # ### find latest session dpath
        # session_pattern = r"^\d{4}$"
        # def _session_sorter(dpath: MyPath):
        #     if re.match(session_pattern, dpath.name):
        #         return int(dpath.name)
        #     else:
        #         return -1
        # lst_ses_dirs = sorted(list(dpath_day.iterdir()), key= _session_sorter)
        # if not lst_ses_dirs:
        #     push_log("保存失败: 当日文件夹是空的", is_error=True)
        #     raise UserInterrupt
        # dpath_ses = lst_ses_dirs[-1]
        # if not re.match(session_pattern, dpath_ses.name):
        #     push_log("保存失败: 当日文件夹中没有任何 session 文件夹", is_error=True)
        #     raise UserInterrupt
        ### 结束 redundant check 并得到最新的 session dpath
        dpath_ses = find_latest_sesframes_folder() # produces UserInterrupt if folder seeking fails
        str_ses = str(dpath_ses.name)
        now = datetime.now()
        timestamp: str = now.strftime("%Y-%m-%d-%H-%M-%S-") + f"{now.microsecond//1000:03d}"
        fpath = dpath_ses /( timestamp + ".tif")
        try: # again, this is a redundant check, I don't think the save will fail, unless there's a Z disk connection problem
            tifffile.imwrite(fpath, self[self.cid])
            return str_ses
        except Exception:
            push_exception("当前帧保存失败")
            raise UserInterrupt
    def clear(self)->None:
        """
        - clear int & float decks
        - cid update
        - avg frame update
        - clear ses label deck
        - cid indicator updates
        - clear all plots
        - clear all plot labels
        """
        super().clear()
        self.float_deck.clear()
        self.cid = None
        self.frame_avg = None
        self.seslabel_deck = []
        dpg.set_value("frame deck display", self.memory_report())
        dpg.set_item_label("cid indicator", "N/A")
        for yax in self.get_all_tags_yaxes():
            dpg.delete_item(yax, children_only=True)
            # print('yax', yax)
            thisPlot = dpg.get_item_parent(yax)
            dpg.configure_item(thisPlot, label = " ")
            # heatmapSlot: List[int] = dpg.get_item_children(yax)[1]
            # print('slot',heatmapSlot)
            # if heatmapSlot:
            #     heatSeries, = heatmapSlot
            #     print('series', heatSeries)
            #     dpg.delete_item(heatSeries)
    def get_all_tags_yaxes(self):
        lst_allyaxes = [map.yAx for map in self.lst_dupe_maps]
        lst_allyaxes.append("frame yax")
        return lst_allyaxes
    @staticmethod
    def _plot_frame(frame: npt.NDArray[np.floating], 
                    # xax: str="frame xax", 
                    yax: str | int = "frame yax")->None:
        assert np.issubdtype(frame.dtype, float), "heatmap frame can only be float!"
        colorbar="frame colorbar"
        fmin, fmax, (nvrows, nhcols) = frame.min(), frame.max(), frame.shape

        plot_mainframe_p = yax == "frame yax" # need this check because we can plot in dupe frame windows
        if dpg.get_value("manual scale checkbox"):
            fmin, fmax, *_ = dpg.get_value("color scale lims")
        elif plot_mainframe_p: # update disabled manual color lim fields. do not do this when plotting elsewhere
            dpg.set_value("color scale lims", [int(fmin), int(fmax), 0, 0])
        else: # 在 dupe heatmap 中 plot 时, 啥都不干
            pass

        if plot_mainframe_p: # always update color bar lims when doing main plot, whether the manual scale checkbox is checked or not
            dpg.configure_item(colorbar, min_scale = fmin, max_scale = fmax)
        
        had_series_child_p = dpg.get_item_children(yax)[1] # plot new series 之前 check 是否有老 series
        if had_series_child_p:
            dpg.delete_item(yax, children_only=True) # this is necessary!
        dpg.add_heat_series(frame, nvrows, nhcols, parent=yax,
                            scale_min=fmin, scale_max=fmax,format="",
                            bounds_min= (0,nvrows), bounds_max= (nhcols, 0)
                            )
    def plot_avg_frame(self, yax= "frame yax"):
        """
        与 plot_cid_frame 一起都是 绘制 main heatmap 的方法
        区别于 plot_frame_dwim (绘制所有 map, 包括 dupe maps)
        x/yax kwargs make it possible to plot else where when needed
        """
        if self.frame_avg is not None:
            self._plot_frame(self.frame_avg, yax)
            thePlot = dpg.get_item_parent(yax)
            dpg.configure_item(thePlot, label = " ")
    def plot_cid_frame(self, yax= "frame yax"):
        """
        与 plot_avg_frame 一起都是 绘制 main heatmap 的方法
        区别于 plot_frame_dwim (绘制所有 map, 包括 dupe maps)
        x/yax kwargs make it possible to plot else where when needed
        """
        if self.cid is not None:
            frame = self.float_deck[self.cid]
            self._plot_frame(frame, yax)
            thePlot = dpg.get_item_parent(yax)
            dpg.configure_item(thePlot, label = self.seslabel_deck[self.cid])
    def plot_frame_dwim(self):
        """
        global update of all maps (main and dupes)
        """
        if dpg.get_value("toggle 积分/单张 map"):
            self.plot_avg_frame()
        else:
            self.plot_cid_frame()
        for dupe_map_items in self.lst_dupe_maps: # update dupe windows
            self._update_dupe_map(dupe_map_items)
    def _update_dupe_map(self, dupe_map: DupeMap,
                        #   yax, inputInt, radioBtn, cBox
                          ):
        """
        根据 duplicated map 的帧序号输入和 radio button 选择, 在给定的 xax, yax 中重绘热图
        这是搭配 llst_items_dupe_maps 使用的函数
        """
        input_id = dpg.get_value(dupe_map.inputInt)
        radio_option = dpg.get_value(dupe_map.radioBtn)
        plot_avg_p = dpg.get_value(dupe_map.cBox)
        if plot_avg_p:
            self.plot_avg_frame(dupe_map.yAx)
        else:
            thePlot = dpg.get_item_parent(dupe_map.yAx)
            if radio_option == "正数帧":
                plot_id = input_id
            else:
                plot_id = input_id+len(self) - 1
            if 0 <= plot_id < len(self):
                frame = self.float_deck[plot_id]
                self._plot_frame(frame, dupe_map.yAx)
                label= self.seslabel_deck[plot_id]
            else:
                dpg.delete_item(dupe_map.yAx, children_only=True)
                label =  " "
            dpg.configure_item(thePlot, label=label)
    def _append_save_plot(self, this_frame: npt.NDArray[np.uint16]):
        """
        在单线程无并发时, 本函数是重排(如果 awg 开启)后的全套任务
        在双线程/双进程并发中, 本函数是 consumer 取得 frame 后的全套任务
        """
        beg = time.time()
        self.append(this_frame)
        if dpg.get_value("autosave"):
            try:
                str_ses = self._find_lastest_sesframes_folder_and_save_frame()
                self.seslabel_deck.append(str_ses)
            except UserInterrupt:
                self.seslabel_deck.append("未保存!")
                # pass # failed save shall not interrupt acquisition
        else:
            self.seslabel_deck.append("未保存!")
        self.plot_frame_dwim()
        hLhRvLvR = dpg.get_item_user_data("frame plot")
        if hLhRvLvR:
            _update_hist(hLhRvLvR, self)
        end = time.time()

        push_log(f"绘图和存储耗时{(end-beg)*1e3:.3f} ms")


def find_latest_camguiparams_json() ->MyPath:
    dpath_day = _find_newest_daypath_in_save_tree(camgui_params_root)
    ### find latest camgui params json file
    # json_pattern = r"^CA[0-9]+$"
    # def _session_sorter(dpath: MyPath):
    #     if re.match(json_pattern, dpath.name):
    #         return int(dpath.name[2:])
    #     else:
    #         return -1
    json_pattern = r'^CA([0-9]+)\.json$'
    def _camgui_json_sorter(fpath: MyPath):
        match = re.match(json_pattern, fpath.name)
        if match:
            return int(match.group(1))
        else:
            return -1
    lst_jsons = sorted(list(dpath_day.iterdir()), key= _camgui_json_sorter)
    if not lst_jsons:
        # push_log("异常: 最新日期的 camgui json 文件夹是空的", is_error=True)
        raise UserInterrupt('异常: 最新日期的 camgui json 文件夹是空的')
    fpath_newest_json = lst_jsons[-1]
    if not re.match(json_pattern, fpath_newest_json.name):
        # push_log("异常: camgui json save tree 最新日期文件夹中没有任何 json 文件", is_error=True)
        raise UserInterrupt('异常: camgui json save tree 最新日期文件夹中没有任何 json 文件')
    return fpath_newest_json

def _dummy_feed_awg(frame):
    pass
def _my_rand_frame(v=2304,h=4096, max=65535)-> np.ndarray:
    myarr = np.random.randint(0,max, size = v*h, dtype=np.uint16)
    return myarr.reshape((v,-1))


def ZYLconversion(frame: np.ndarray)->np.ndarray:
    """
    ZYL formula to infer photon counts
    """
    frame = (frame -300) * 0.1/0.9
    return frame

def _update_hist(hLhRvLvR: tuple, frame_deck: FrameDeck, yax = "hist plot yax")->None:
    """
    hLhRvLvR 保存了一个矩形选区所包裹的像素中心点坐标（只能是半整数）h 向最小最大值和 v 向最小最大值。
    这些值确定了所选取的像素集合。然后，在此选择基础上将 frame deck 中的每一张 frame 在该选区中的部分的 counts 求得，
    加入 histdata 数据列表
    """
    hLlim, hRlim, vLlim, vRlim = hLhRvLvR
    vidLo, vidHi = math.floor(vLlim), math.floor(vRlim)
    hidLo, hidHi = math.floor(hLlim), math.floor(hRlim)
    histData = []
    for frame in frame_deck.float_deck: # make hist data
        frame = ZYLconversion(frame)
        subFrame = frame[vidLo:vidHi+1, hidLo:hidHi+1]
        histData.append(subFrame.sum())
    dpg.delete_item(yax,children_only=True) # delete old hist, then get some hist params for new plot
    binning = dpg.get_value("hist binning input")
    theMinInt, theMaxInt = math.floor(min(histData)), math.floor(max(histData))
    nBins = (theMaxInt-theMinInt)//binning + 1
    max_range = theMinInt + nBins*binning
    dpg.add_histogram_series(
        histData, parent = yax, bins =nBins, 
        min_range=theMinInt,max_range=max_range)

def st_workerf_flagged_do_all(
    cam: DCAM.DCAM.DCAMCamera,
    flag: threading.Event,
    frame_deck: FrameDeck,
    controller: DDSRampController, # type is DDSRampController, not hinted because it acts funny on macOS
    )-> None:
    """
    single-thread approach worker function which is flagged and does everythig:
    1. acquire frame from camera
    2. feed frame to AWG
    3. append frame to frame_deck
    4. plot frame
    """
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"] 
    awg_params = collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame :npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            beg = time.time()
            feed_AWG(this_frame, controller, awg_params) # feed original uint16 format to AWG
            end = time.time()
            push_log(f"重排前序计算耗时 {(end-beg)*1e3:.3f} ms")
        # beg = time.time()
        # frame_deck.append(this_frame)
        # frame_deck.plot_frame_dwim()
        # hLhRvLvR = dpg.get_item_user_data("frame plot")
        # if hLhRvLvR:
        #     _update_hist(hLhRvLvR, frame_deck)
        # try:
        #     frame_deck._find_lastest_sesframes_folder_and_save_frame()
        # except UserInterrupt:
        #     pass
        # end = time.time()
        # push_log(f"绘图和存储耗时{(end-beg)*1e3:.3f} ms")
        frame_deck._append_save_plot(this_frame)
    cam.stop_acquisition()
    cam.set_trigger_mode("int")

def _dummy_st_workerf_flagged_do_all(
        flag: threading.Event, 
        frame_deck: FrameDeck):
    from fake_frames_imports import frame_list
    while flag.is_set():
        time.sleep(1)
        if frame_list:
            this_frame = frame_list.pop()
            # beg = time.time()          
            # frame_deck.append(this_frame)
            # frame_deck.plot_frame_dwim()
            # hLhRvLvR = dpg.get_item_user_data("frame plot")
            # if hLhRvLvR:
            #     _update_hist(hLhRvLvR, frame_deck)
            # try:
            #     frame_deck._find_lastest_sesframes_folder_and_save_frame()
            # except UserInterrupt:
            #     pass
            # end = time.time()
            # push_log(f"绘图和存储耗时{(end-beg)*1e3:.3f} ms")
            frame_deck._append_save_plot(this_frame)
        else:
            break

#### objects for dual thread approach
_mt_dummy_remote_buffer = queue.Queue(maxsize=500) # 假相机 buffer, 双线程方案
_local_buffer = queue.SimpleQueue() # 双进程和双线程通用
def _workerf_dummy_remote_buffer_feeder(
        q: queue.Queue = _mt_dummy_remote_buffer)-> None:
    """
    假相机 buffer 的 filler, 由假触发 checkbox 控制是否向假相机 buffer 中放 frame
    """
    # print("feeder launched")
    from fake_frames_imports import frame_list
    frame_list_ = copy.deepcopy(frame_list)
    del frame_list
    while True:
        time.sleep(1) # simulate snap rate
        if dpg.get_value("假触发"):
            if frame_list_:
                this_frame = frame_list_.pop()
                q.put(this_frame)
            else:
                push_log("已向假相机 mt buffer 发送 500 帧", is_good=True)
                break
def _dummy_mt_producerf_polling_do_snag_rearrange_deposit(
        flag: threading.Event,
        q: queue.Queue = _mt_dummy_remote_buffer,
        qlocal: queue.SimpleQueue = _local_buffer,
        )->None:
    """
    假 producer
    从假相机 buffer 中取 frame, 放入 local buffer
    polling a flag. flag clear 时, 投毒, 停止循环
    """
    while flag.is_set():
        try:
            this_frame: npt.NDArray[np.uint16] = q.get(timeout=0.2)
        except queue.Empty:
            continue
        time.sleep(0.01) # 模拟重排耗时
        qlocal.put(this_frame)
    qlocal.put(None) # poison pill

def consumerf_local_buffer(
        frame_deck: FrameDeck,
        qlocal: queue.SimpleQueue = _local_buffer, 
        )->None:
    """
    consumer (双线程和双进程通用)
    从 local buffer 中取 frame, 然后:
    1. 放入 frame deck
    2. 绘图
    3. 保存帧
    """
    while True:
        time.sleep(0.01)
        this_frame = qlocal.get()
        if this_frame is None: # poison pill
            break # looping worker killed
        # frame_deck.append(this_frame)
        # frame_deck.plot_frame_dwim()
        # hLhRvLvR = dpg.get_item_user_data("frame plot")
        # if hLhRvLvR:
        #     _update_hist(hLhRvLvR, frame_deck)
        # try:
        #     frame_deck._find_lastest_sesframes_folder_and_save_frame()
        # except UserInterrupt: # UserInterrupts are exceptions with well known cause, we keep acquisition without interruption. Strange exceptions would still interrupt acquisition
        #     pass
        frame_deck._append_save_plot(this_frame)

def mt_producerf_polling_do_snag_rearrange_deposit(
        cam: DCAM.DCAM.DCAMCamera,
        flag: threading.Event,
        controller, # type is DDSRampController, not hinted because it acts funny on macOS
        local_buffer: queue.SimpleQueue = _local_buffer,
        )->None:
    """
    双线程 producer,
    从 camera 中取 frame, 放入 local buffer
    polling a flag, flag clear 时, 投毒, 终止
    """
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"] 
    awg_params = collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame: npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            beg = time.time()
            feed_AWG(this_frame, controller, awg_params)
            end = time.time()
            push_log(f"重排前序计算耗时 {(end-beg)*1e3:.3f} ms")
        local_buffer.put(this_frame)
    cam.stop_acquisition()
    cam.set_trigger_mode("int")
    local_buffer.put(None) # poison pill    

### dual processes approach 需要的 objects:
# conn_sig_main, conn_sig_child = multiprocessing.Pipe()
# conn_frame_main, conn_frame_child = multiprocessing.Pipe()
# import copy
# frame_list_ = copy.deepcopy(frame_list) # mp 方案专用的假数据
# _mp_dummy_remote_buffer = multiprocessing.Queue()
def _mp_workerf_dummy_remote_buffer_feeder(
        q: multiprocessing.Queue)-> None:
    """
    假相机 buffer 的 feeder, 这里的假 buffer 是一个 multiprocessing.Queue,
    由主线程填充, 由假触发 checkbox 控制是否向假 buffer 中放 frame
    """
    from fake_frames_imports import frame_list
    frame_list_ = copy.deepcopy(frame_list)
    del frame_list
    while True:
        time.sleep(1) # simulate snap rate
        if dpg.get_value("假触发"):
            if frame_list_:
                this_frame = frame_list_.pop()
                q.put(this_frame)
                # print("fed frame")
            else:
                push_log("已向假相机 mp buffer 发送 500 帧", is_good=True)
                break

# def _mp_pass_hello(conn: multiprocessing.connection.Connection):
#     conn.send("hello")
#     conn.close()

def _dummy_mp_producerf_polling_do_snag_rearrange_send(
        conn_sig: multiprocessing.connection.Connection,
        conn_data: multiprocessing.connection.Connection,
        conn_debug: multiprocessing.connection.Connection,
        q: multiprocessing.Queue
        ):
    # conn_debug.send("inside")
    while not conn_sig.poll():
        # conn_debug.send("looping")
        try:
            this_frame: npt.NDArray[np.uint16] = q.get(timeout=0.2)
            # conn_debug.send("produced frame")
        except queue.Empty:
            continue
        time.sleep(0.01) # 模拟重排耗时
        conn_data.send(this_frame)
    conn_sig.close()
    conn_data.send(None) # poison pill
    conn_data.close()
    conn_debug.close()


def mp_producerf_polling_do_snag_rearrange_send(
        conn_sig: multiprocessing.connection.Connection,
        conn_data: multiprocessing.connection.Connection,
        cam_params: Sequence[float],
        awg_is_on: bool, # 这个 bool 不能在放 body 中获取, 因为 body 是在新进程中运行, 而在新进程中, main guard 阻止了这个 producer 接触一切 gui 相关代码
        awg_params: Sequence # 无论 awg 是否开启都必须加上, 因为 multiprocessing.Process 的 args 参数是固定的
        ):
    """
    双进程 producer, 运行于从进程
    打开 cam, 设置 camera, 打开 awg (如果 gui 开了)
    从 camera 中取 frame, 重排 (如果 gui 开了), 然后放入 data pipe
    polling signal pipe, 当收到 signal 时, 关闭 cam, 关闭 awg (如果 gui 开了), 投毒
    """
    if awg_is_on:
        raw_card, controller = gui_open_awg()
    exposure, hstart, hend, vstart, vend, hbin, vbin = cam_params
    cam = DCAM.DCAMCamera() # 无论是否需要 awg, cam obj 是一定需要的
    cam.open()
    cam.set_exposure(exposure)
    cam.set_roi(hstart, hend, vstart, vend, hbin, vbin)
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes = 100)
    conn_sig.send('cam all set in the alternative session')
    while not conn_sig.poll():
        try:
            cam.wait_for_frame(timeout = 0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame: npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            feed_AWG(this_frame, controller, awg_params)
        conn_data.send(this_frame)
    if awg_is_on:
        raw_card.close()
        controller = None # for possible garbage collection
    cam.close()
    conn_sig.close()
    conn_data.send(None) # poison pill
    conn_data.close()

def mp_passerf(
        conn: multiprocessing.connection.Connection,
        q: queue.SimpleQueue = _local_buffer):
    while True:
        this_frame = conn.recv()
        q.put(this_frame)
        if this_frame is None:
            conn.close()
            break

def _log(sender, app_data, user_data):
    """
    helper function from demo.py. 可以作为还没写好的 callback 的 placeholder，
    coding 时用来查看 callback 的所有三个 argument：
    - sender：the id of the UI item that submitted teh callback
    - app_data: occasionally UI items will send their own data (e.g. file dialog)
    - user_data: any python object you want to send to the function
    (quoted from dpg online doc)
    """
    print(f"sender: {sender}, \t app_data: {app_data}, \t user_data: {user_data}")

def rgb_opposite(r, g, b):
    """
    给出某 rgb 相对最大对比度颜色（HSL approach）。@GPT
    """
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255) # convert to HSL
    h = (h + 0.5) % 1.0 # Rotate hue by 180° (opposite color)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s) # Convert back to RGB
    return int(r2*255), int(g2*255), int(b2*255)

def gui_open_awg():
    raw_card = spcm.Card(card_type = spcm.SPCM_TYPE_AO)
    raw_card.open()
    controller = DDSRampController(raw_card)
    return raw_card, controller

def collect_awg_params() -> tuple:
    x1, y1, *_ = dpg.get_value("x1 y1")
    x2, y2, *_ = dpg.get_value("x2 y2")
    x3, y3, *_ = dpg.get_value("x3 y3")
    nx, ny, *_ = dpg.get_value("nx ny")
    x0, y0, *_ = dpg.get_value("x0 y0")
    rec_x, rec_y, *_ = dpg.get_value("rec_x rec_y")
    count_threshold = dpg.get_value("count_threshold")
    n_packed = dpg.get_value("n_packed")
    start_frequency_on_row, start_frequency_on_col, *_ = dpg.get_value("start_frequency_on_row(col)")
    start_frequency_on_row*= 1e6
    start_frequency_on_col*= 1e6
    end_frequency_on_row, end_frequency_on_col, *_ = dpg.get_value("end_frequency_on_row(col)")
    end_frequency_on_row*=1e6
    end_frequency_on_col*=1e6
    start_site_on_row, start_site_on_col, *_ = dpg.get_value("start_site_on_row(col)")
    end_site_on_row, end_site_on_col, *_ = dpg.get_value("end_site_on_row(col)")
    num_segments = dpg.get_value("num_segments")
    power_ramp_time = dpg.get_value("power_ramp_time (ms)")
    power_ramp_time*=1e-3
    move_time = dpg.get_value("move_time (ms)")
    move_time *= 1e-3
    percentage_total_power_for_list = dpg.get_value("percentage_total_power_for_list")
    ramp_type = dpg.get_value("ramp_type")
    user_tgt_arr_input = dpg.get_value("target array binary text input")
    lines = user_tgt_arr_input.replace(" ", "").strip().splitlines()
    tgt2darr = np.array([[int(ch) for ch in line] for line in lines if line != ""], dtype=int)
    return (x1,y1, x2, y2, x3, y3, nx, ny, x0, y0, rec_x, rec_y, count_threshold,
            n_packed, start_frequency_on_row, start_frequency_on_col,
            end_frequency_on_row, end_frequency_on_col,
            start_site_on_row, start_site_on_col,
            end_site_on_row, end_site_on_col,
            num_segments, power_ramp_time, move_time,
            percentage_total_power_for_list, ramp_type, tgt2darr)
# with dpg.theme() as theme_error_blinking:
#     with dpg.theme_component(dpg.mvChildWindow):
#         dpg.add_theme_color(dpg.mvThemeCol_FrameBg, )

_bullets = cycle(["-", "*", "+", "•", "°"])
def _push_log(msg:str, *, 
             is_error: bool=False,
             is_good: bool=False,
             is_warning = False):
    """
    将 message 显示在 log window 中
    仅仅在 context 创建完毕后有效
    """
    tagWin = "log window"
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.") + f"{now.microsecond//1000:03d}"
    if is_error:
        color = (255,0,0)
    elif is_good:
        color = (0,255,0)
    elif is_warning:
        color = (255,222,33)
    else:
        color = None
    dpg.add_text(next(_bullets)+timestamp+"\n"+msg, 
                parent= tagWin, 
                color = color,
                wrap= 150)
    
    win_children: Dict[int, List[int]] = dpg.get_item_children(tagWin)
    lst_tags_msgs = win_children[1]
    if len(lst_tags_msgs)>100: # log 最多 100 条
        oldestTxt = lst_tags_msgs.pop(0)
        dpg.delete_item(oldestTxt)

    dpg.set_y_scroll(tagWin, dpg.get_y_scroll_max(tagWin)+20 # the +20 is necessary because IDK why the window does not scroll to the very bottom, there's a ~20 margin, strange. 
                    )

def push_log(*args, **kwargs):
    """
    context 创建过程中, 就可以预先设置在 camgui 启动后显示的异常
    """
    if dpg.is_dearpygui_running():
        _push_log(*args, **kwargs)
    else:
        dpg.set_frame_callback(3, lambda: _push_log(*args, **kwargs))
# def push_exception3(
#         e: Exception, 
#         user_msg: str # force myself to give a user friendly comment about what error might have happened
#         ):
#     """
#     在 catch exception 的时候, 在 log window 显示 exception (因为 gui 没有 REPL)
#     """
#     push_log(user_msg 
#              + "\n" 
#              + f"exception type: {type(e).__name__}\nexception msg: {e}",
#                             is_error=True)
def push_exception(user_msg: str=""):
    """
    在 camgui log window 中显示 traceback 的 exception
    """
    # traceback.print_exc() # for REPL review
    push_log(user_msg 
             + "\n" 
             + traceback.format_exc(), is_error=True)

CamguiParams = namedtuple(typename='CamguiParams',
                          field_names=[ # the point of namedtuple is to fix these keys 
                              '并发方式',
                              'cam面板参数',
                              'awg面板参数',
                              'Camgui版本',
                              ],
                              defaults = [camgui_ver])
def save_camgui_json_to_savetree():
    panel_params = CamguiParams( # 先把能直接 dpg.get_value 的 string tag 排好, 如果 tag 有拼写错误, 接下来在 dpg.get_value 时就会报错
        并发方式 = {
            '无并发: 单线程采集重排绘图保存' : None,
            '双线程: 采集重排 & 绘图保存' : None,
            '双进程: 采集重排 & 绘图保存' : None,
        },
        cam面板参数 = {
            'exposure field' : None,
            'h start & h length:' : None,
            'v start & v length:' : None,
            'h binning & v binning' : None,
        },
        awg面板参数 = {
            'awg is on' : dpg.get_item_user_data('AWG toggle')['is on'],
            'x1 y1' : None,
            'x2 y2' : None,
            'x3 y3' : None,
            'nx ny' : None,
            'x0 y0' : None,
            'rec_x rec_y' : None,
            'count_threshold' : None,
            'n_packed' : None,
            "start_frequency_on_row(col)" : None,
            "end_frequency_on_row(col)" : None,
            "start_site_on_row(col)" : None,
            "end_site_on_row(col)" : None,
            'num_segments' : None,
            'power_ramp_time (ms)' : None,
            'move_time (ms)' : None,
            'percentage_total_power_for_list' : None,
            'ramp_type' : None,
            'target array binary text input' : None,
            })
    for key in panel_params.并发方式:
        panel_params.并发方式[key] = dpg.get_value(key)
    for key in panel_params.cam面板参数:
        panel_params.cam面板参数[key] = dpg.get_value(key)
    for key in panel_params.awg面板参数:
        if key != 'awg is on':
            panel_params.awg面板参数[key] = dpg.get_value(key)
    dpath_day = _mk_save_tree_from_root_to_day(camgui_params_root)
    extra_confirm = False
    if dpath_day.exists():
        try:
            fpath_newest_json = find_latest_camguiparams_json()
            json_num_latest = int((fpath_newest_json.name[2:])[:-5]) #掐头去尾, 从 e.g. CA100.json 得到 100
            new_str_json = 'CA' + str(json_num_latest + 1) + '.json'
        except UserInterrupt:
            push_exception('保存 camgui json 文件时发现异常')
            new_str_json = 'CA1.json'
            extra_confirm = True
    else:
        dpath_day.mkdir(parents=True)
        new_str_json = 'CA1.json'
        # lst_json_fpaths = list(dpath_day.iterdir())
        # if lst_json_fpaths:  # 防止 day dir 是空的, 这种情况只可能发生在用户手动清空 day dir 的时候
        #     ...
        # else:
        #     new_json_name = 'CA1.json'
    fpath = dpath_day / new_str_json
    # print(fpath)
    with open(fpath, 'w') as f:
        json.dump(panel_params._asdict(), f, 
                  indent = 2, # @GPT more human-readable
                  ensure_ascii=False # to save chinese
                  )
    if extra_confirm:
        push_log('虽然有异常, 但是 camgui json 文件夹依然创建成功', is_good =True)
    return new_str_json
    # fpath.mkdir(parents = True)