# pyright: reportOptionalSubscript=false
"""
camgui 相关的帮助函数
"""
#%%
import traceback
import queue
import time
import numpy.typing as npt
from typing import List, Dict
import re
from deprecated import deprecated
import math
from datetime import datetime
from pylablib.devices import DCAM
import numpy as np
import threading
import colorsys
import tifffile
from .dirhelper import MyPath, session_frames_root, month_dict
import dearpygui.dearpygui as dpg
import platform, uuid
system = platform.system()
if (system == "Windows") and (hex(uuid.getnode()) != '0xf4ce2305b4c7'): # the code stands for A402 computer
    import spcm
    from AWG_module.no_with_func import DDSRampController
    from AWG_module.unified import feed_AWG

class UserInterrupt(Exception):
    """
    打断 callback 所用的 exception
    """
    pass

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
        # self.frames_root  = MyPath(frames_root_str)
        self.cid: int | None = None # current heatmap's id in deck
        self.float_deck: List[npt.NDArray[np.floating]] = [] # gui 中的操作需要 float frame, 因此与 list (int deck) 对应, 要有一个 float deck
        self.frame_avg: npt.NDArray[np.floating] | None = None
        self.llst_items_dupe_maps : List[List[int | str]] = [] # 保存 duplicated heatmaps window 中的 item tuple
    def memory_report(self) -> str:
        len_deck = len(self)
        if len_deck > 0:
            mbsize_1_int_frame = self[0].nbytes/ (1024**2)
            mbsize_1_float_frame = self.float_deck[0].nbytes/ (1024**2)
        else:
            mbsize_1_int_frame = mbsize_1_float_frame = 0
        return f"内存: {len_deck} 帧 ({(mbsize_1_float_frame+mbsize_1_int_frame)*len_deck:.2f} MB)"
    @deprecated
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
    @deprecated
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
                except Exception as e:
                    push_exception(e, f"帧 #{i} 保存失败.")
                
            push_log("全部帧保存成功", is_good=True)
        else:
            push_log("内存中没有任何帧", is_error=True)
    @deprecated
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
            except Exception as e:
                push_exception(e, "当前帧保存失败")
                return
            push_log("当前帧保存成功", is_good=True)
        else:
            push_log("内存中没有任何帧", is_error=True)
    def _find_lastest_sesframes_folder_and_save_frame(self):
        """
        本函数会做非常 redundant 的 check,
        除非奇怪的事情发生, 比如数据丢失,
        否则创建 session frames 目录下不会出现会被报错的情况,
        比如有 2025 年下是空的, 连一月文件夹都没有. 
        这种情况在用 mkdir_session_frames() 当前 session 文件夹时不会发生
        """
        ### 开始 redundant check
        if not session_frames_root.exists():
            push_log("没有找到 session dir, 请检查 Z 盘是否连接", is_error=True)
            raise UserInterrupt
        if not session_frames_root.is_writable():
            push_log("目标路径不可写", is_error=True)
            raise UserInterrupt
        ### find latest year dpath
        year_pattern = r"2\d{3}$" # A105 不可能存活到 3000 年
        def _year_sorter(dpath: MyPath):
            if re.match(year_pattern, dpath.name):
                return int(dpath.name)
            else:
                return -1 # 其他我不关心的东西都排最前面
        lst_year_dirs = sorted(list(session_frames_root.iterdir()), key= _year_sorter)
        if not lst_year_dirs:
            push_log("保存失败: 帧数据路径是空的", is_error=True)
            raise UserInterrupt
        dpath_year = lst_year_dirs[-1]
        if not re.match(year_pattern, dpath_year.name):
            push_log("保存失败: 帧数据路径中没有任何文件夹", is_error=True)
            raise UserInterrupt
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
            push_log("保存失败: 当年文件夹是空的", is_error=True)
            raise UserInterrupt
        dpath_month = lst_month_dirs[-1]
        if dpath_month.name not in month_sort_dict:
            push_log("保存失败: 当年文件夹中没有任何月份文件夹", is_error=True)
            raise UserInterrupt
        ### find latest day dpath
        day_pattern = r"^\d{2}$"
        def _day_sorter(dpath: MyPath):
            if re.match(day_pattern, dpath.name):
                return int(dpath.name)
            else:
                return -1
        lst_day_dirs = sorted(list(dpath_month.iterdir()), key= _day_sorter)
        if not lst_day_dirs:
            push_log("保存失败: 当月文件夹是空的", is_error=True)
            raise UserInterrupt
        dpath_day = lst_day_dirs[-1]
        if not re.match(day_pattern, dpath_day.name):
            push_log("保存失败: 当月文件夹中没有任何日期文件夹", is_error=True)
            raise UserInterrupt
        ### find latest session dpath
        session_pattern = r"^\d{4}$"
        def _session_sorter(dpath: MyPath):
            if re.match(session_pattern, dpath.name):
                return int(dpath.name)
            else:
                return -1
        lst_ses_dirs = sorted(list(dpath_day.iterdir()), key= _session_sorter)
        if not lst_ses_dirs:
            push_log("保存失败: 当日文件夹是空的", is_error=True)
            raise UserInterrupt
        dpath_ses = lst_ses_dirs[-1]
        if not re.match(session_pattern, dpath_ses.name):
            push_log("保存失败: 当日文件夹中没有任何 session 文件夹", is_error=True)
            raise UserInterrupt
        ### 结束 redundant check 并得到最新的 session dpath
        now = datetime.now()
        timestamp: str = now.strftime("%Y-%m-%d-%H-%M-%S-") + f"{now.microsecond//1000:03d}"
        fpath = dpath_ses /( timestamp + ".tif")
        try: # again, this is a redundant check, I don't think the save will fail, unless there's a Z disk connection problem
            tifffile.imwrite(fpath, self[self.cid])
        except Exception as e:
            push_exception(e, "当前帧保存失败")
            raise UserInterrupt
    def clear(self)->None:
        """
        - clear int & float decks
        - cid update
        - avg frame update
        - cid indicator updates
        - clear all plots
        """
        super().clear()
        self.float_deck.clear()
        self.cid = None
        self.frame_avg = None
        dpg.set_value("frame deck display", self.memory_report())
        dpg.set_item_label("cid indicator", "N/A")
        for yax in self.get_all_tags_yaxes():
            heatmapSlot: List[int] = dpg.get_item_children(yax)[1] # type: ignore
            if heatmapSlot:
                heatSeries, = heatmapSlot
                dpg.delete_item(heatSeries)
    def get_all_tags_yaxes(self):
        lst_allyaxes = [yax for _, yax, *_ in self.llst_items_dupe_maps]
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
        
        had_series_child_p = dpg.get_item_children(yax)[1] # type: ignore # plot new series 之前 check 是否有老 series
        if had_series_child_p:
            dpg.delete_item(yax, children_only=True) # this is necessary!
        dpg.add_heat_series(frame, nvrows, nhcols, parent=yax, # type: ignore
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
    def plot_cid_frame(self, yax= "frame yax"):
        """
        与 plot_avg_frame 一起都是 绘制 main heatmap 的方法
        区别于 plot_frame_dwim (绘制所有 map, 包括 dupe maps)
        x/yax kwargs make it possible to plot else where when needed
        """
        if self.cid is not None:
            frame = self.float_deck[self.cid]
            self._plot_frame(frame, yax)
    def plot_frame_dwim(self):
        """
        global update of all maps (main and dupes)
        """
        if dpg.get_value("toggle 积分/单张 map"):
            self.plot_avg_frame()
        else:
            self.plot_cid_frame()
        for dupe_map_items in self.llst_items_dupe_maps: # update dupe windows
            self._update_dupe_map(*dupe_map_items)
    def _update_dupe_map(self, yax, inputInt, radioBtn, cBox):
        """
        根据 duplicated map 的帧序号输入和 radio button 选择, 在给定的 xax, yax 中重绘热图
        这是搭配 llst_items_dupe_maps 使用的函数
        """
        input_id = dpg.get_value(inputInt)
        radio_option = dpg.get_value(radioBtn)
        plot_avg_p = dpg.get_value(cBox)
        if plot_avg_p:
            self.plot_avg_frame(yax)
        else:
            if radio_option == "正数帧":
                plot_id = input_id
            else:
                plot_id = input_id+len(self) - 1
            if 0 <= plot_id < len(self):
                frame = self.float_deck[plot_id]
                self._plot_frame(frame, yax)
            else:
                dpg.delete_item(yax, children_only=True)


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


# def start_flag_watching_acq_buffer_rearrange(
#     cam: DCAM.DCAM.DCAMCamera,
#     flag: threading.Event,
#     frame_deck: FrameDeck,
#     controller, # type is DDSRampController, not hinted because it acts funny on macOS
#     )-> None:
    
#     cam.set_trigger_mode("ext")
#     cam.start_acquisition(mode="sequence", nframes=100)
#     awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"]
#     awg_params = _collect_awg_params()
#     while flag.is_set():
#         try:
#             cam.wait_for_frame(timeout=0.2)
#         except DCAM.DCAMTimeoutError:
#             continue
#         this_frame: npt.NDArray[np.uint16] = cam.read_oldest_image()
#         if awg_is_on:
#             feed_AWG(this_frame, controller, awg_params) # feed original uint16 format to AWG

#         frame_deck.append(this_frame)
#         frame_deck.plot_frame_dwim()
#         hLhRvLvR = dpg.get_item_user_data("frame plot")
#         if hLhRvLvR:
#             _update_hist(hLhRvLvR, frame_deck)
#         # print("frame acquired")

def st_workerf_flagged_do_all(
    cam: DCAM.DCAM.DCAMCamera,
    flag: threading.Event,
    frame_deck: FrameDeck,
    controller, # type is DDSRampController, not hinted because it acts funny on macOS
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
    awg_params = _collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame :npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            feed_AWG(this_frame, controller, awg_params) # feed original uint16 format to AWG
        frame_deck.append(this_frame)
        frame_deck.plot_frame_dwim()
        hLhRvLvR = dpg.get_item_user_data("frame plot")
        if hLhRvLvR:
            _update_hist(hLhRvLvR, frame_deck)

    cam.stop_acquisition()
    cam.set_trigger_mode("int")

from fake_frames_imports import frame_list
def _dummy_st_workerf_flagged_do_all(
        flag: threading.Event, 
        frame_deck: FrameDeck):
    while flag.is_set():
        time.sleep(1)
        if frame_list:
            this_frame = frame_list.pop()
            beg = time.time()            
            frame_deck.append(this_frame)
            frame_deck.plot_frame_dwim()
            hLhRvLvR = dpg.get_item_user_data("frame plot")
            if hLhRvLvR:
                _update_hist(hLhRvLvR, frame_deck)
            end = time.time()
            push_log(f"绘图耗时{(end-beg)*1e3:.3f} ms")
        else:
            break

#### objects for dual thread approach
_dummy_remote_buffer = queue.Queue(maxsize=1) # 假相机 buffer
_local_buffer = queue.SimpleQueue()
def _workerf_dummy_remote_buffer_feeder(
        q: queue.Queue = _dummy_remote_buffer)-> None:
    """
    假相机 buffer 的 filler, 由假触发 checkbox 控制是否向假相机 buffer 中放 frame
    """
    print("feeder launched")
    while True:
        time.sleep(1) # simulate snap rate
        if dpg.get_value("假触发"):
            if frame_list:
                this_frame = frame_list.pop()
                q.put(this_frame)
                print("fake snap done")
            else:
                push_log("已向假相机 buffer 发送 500 帧", is_error=True)
                break
def _dummy_dt_producerf_flagged_do_snap_rearrange_deposit(
        flag: threading.Event,
        q: queue.Queue = _dummy_remote_buffer,
        qlocal: queue.SimpleQueue = _local_buffer,
        )->None:
    """
    假 producer
    从假相机 buffer 中取 frame, 放入 local buffer
    """
    while flag.is_set():
        try:
            this_frame: npt.NDArray[np.uint16] = q.get(timeout=0.2)
        except queue.Empty:
            continue
        time.sleep(0.1) # 模拟重排耗时
        qlocal.put(this_frame)
    qlocal.put(None) # poison pill

def consumerf_local_buffer(
        frame_deck: FrameDeck,
        qlocal: queue.SimpleQueue = _local_buffer, 
        )->None:
    """
    consumer
    从 local buffer 中取 frame, 然后:
    1. 放入 frame deck
    2. 绘图
    3. 保存帧
    """
    while True:
        this_frame = qlocal.get()
        if this_frame is None: # poison pill
            break # looping worker killed
        frame_deck.append(this_frame)
        frame_deck.plot_frame_dwim()
        hLhRvLvR = dpg.get_item_user_data("frame plot")
        if hLhRvLvR:
            _update_hist(hLhRvLvR, frame_deck)
        try:
            frame_deck._find_lastest_sesframes_folder_and_save_frame()
        except UserInterrupt:
            pass

def dt_producerf_flagged_do_snap_rearrange_deposit(
        cam: DCAM.DCAM.DCAMCamera,
        flag: threading.Event,
        controller, # type is DDSRampController, not hinted because it acts funny on macOS
        local_buffer: queue.SimpleQueue = _local_buffer,
        )->None:
    """
    双线程 worker1,
    从 camera 中取 frame, 放入 local buffer
    watching a flag, flag clear 时, 投毒, 终止
    """
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"] 
    awg_params = _collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame: npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            feed_AWG(this_frame, controller, awg_params)
        local_buffer.put(this_frame)
    local_buffer.put(None) # poison pill    
    cam.stop_acquisition()
    cam.set_trigger_mode("int")


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

def _collect_awg_params() -> tuple:
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


def push_log(msg:str, *, 
             is_error: bool=False, is_good: bool=False):
    """
    将 message 显示在 log window 中
    TODO: add a visual bell background blinking upon error
    """
    tagWin = "log window"
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.") + f"{now.microsecond//1000:03d}"
    if is_error:
        color = (255,0,0)
    elif is_good:
        color = (0,255,0)
    else:
        color = None
    dpg.add_text("- "+timestamp+"\n"+msg, 
                 parent= tagWin, 
                 color = color, # type: ignore
                 wrap= 150)
    
    win_children: Dict[int, List[int]] = dpg.get_item_children(tagWin) # type: ignore
    lst_tags_msgs = win_children[1]
    if len(lst_tags_msgs)>100: # log 最多 100 条
        oldestTxt = lst_tags_msgs.pop(0)
        dpg.delete_item(oldestTxt)

    dpg.set_y_scroll(tagWin, dpg.get_y_scroll_max(tagWin)+20 # the +20 is necessary because IDK why the window does not scroll to the very bottom, there's a ~20 margin, strange. 
                     )

def push_exception(
        e: Exception, 
        user_msg: str # force myself to give a user friendly comment about what error might have happened
        ):
    """
    在 catch exception 的时候, 在 log window 显示 exception (因为 gui 没有 REPL)
    """
    push_log(user_msg 
             + "\n" 
             + f"exception type: {type(e).__name__}\nexception msg: {e}",
                            is_error=True)
def push_exception2(user_msg: str=""):
    """
    在 catch exception 的时候, 在 log window 显示 exception (因为 gui 没有 REPL)
    """

    push_log(user_msg 
             + "\n" 
             + traceback.format_exc(), is_error=True)

    