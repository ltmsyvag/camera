"""
camgui 相关的帮助函数
"""
#%%
import math
from datetime import datetime
from pathlib import Path
from pylablib.devices import DCAM
import numpy as np
import threading
import colorsys
import tifffile
import os
import dearpygui.dearpygui as dpg
import platform, uuid
system = platform.system()
if (system == "Windows") and (hex(uuid.getnode()) != '0xf4ce2305b4c7'): # the code stands for A402 computer
    import spcm
    from .AWG_module.no_with_func import DDSRampController
    from .AWG_module.unified import feed_AWG

class FrameDeck(list):
    """
    class of a special list with my own methods for manipulating the frames it stores
    """
    cid = None # current heatmap's id in deck
    float_deck = [] # gui 中的操作需要 float frame, 因此与 list (int deck) 对应, 要有一个 float deck
    def memory_report(self) -> str:
        len_deck = len(self)
        if len_deck > 0:
            mbsize_1_int_frame = self[0].nbytes/ (1024**2)
            mbsize_1_float_frame = self.float_deck[0].nbytes/ (1024**2)
        else:
            mbsize_1_int_frame = mbsize_1_float_frame = 0
        return f"内存: {len_deck} 帧 ({(mbsize_1_float_frame+mbsize_1_int_frame)*len_deck:.2f} MB)"
    
    def _force_update(self):
        """
        强制 float_deck 和与 list 内容同步, overhead 可能较大, 在需要的时候使用
        同时执行:
        - 更新 deck counts 显示
        - 调整 cid 到 deck 最末
        """
        if self:
            self.float_deck = [e.astype(float) for e in self]
            self.cid = len(self) - 1
            dpg.set_value("frame deck display", self.memory_report())
            self.plot_frame_dwim()
    
    def _make_savename_stub(self):
        """
        如果想保存的文件时间是
        "C:\\Users\\username\\Desktop\\2023-10-01-12-00-00_id.tiff",
        那么在 Desktop 存在并可写入, 且 frame deck 非空的情况下, 返回字符串形式的 stub
        "C:\\Users\\username\\Desktop\\2023-10-01-12-00-00"
        """
        if self:
            saveroot = MyPath(dpg.get_value("save path input field"))
            if saveroot.is_dir() and saveroot.is_writable():
                timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                fpath_stub = str(saveroot / timestamp)
                return fpath_stub
    def save_deck(self):
        """
        保存全部 frames, 如果保存成功/失败, 返回 True/False
        """
        fpath_stub = self._make_savename_stub()
        if fpath_stub:
            for i, self in enumerate(self):
                fpath = fpath_stub + f"_{i}.tiff"
                tifffile.imwrite(fpath, self)
                
            return True # saved
        else:
            return False
    def save_cid_frame(self)->bool:
        """
        保存 cid 指向的 frame, 如果保存成功/失败, 返回 True/False
        """
        fpath_stub = self._make_savename_stub()
        if fpath_stub:
            fpath = fpath_stub + f"_{self.cid}.tiff"
            tifffile.imwrite(fpath, self[self.cid])
            return True # saved
        else:
            return False # not saved
    def append(self, frame: np.ndarray):
        """
        append a new frame to int & float decks
        同时执行: 
        - cid update
        - counts display update
        - cid indicator updates
        """
        # print(frame.dtype)
        assert frame.dtype == np.uint16, "frame should be uint16, something's off?!"

        super().append(frame)
        self.float_deck.append(frame.astype(float))
        self.cid = len(self) - 1
        dpg.set_value("frame deck display", self.memory_report())
        dpg.set_item_label("cid indicator", f"{self.cid+1}/{len(self)}")
    def clear(self):
        """
        clear int & float decks
        """
        super().clear()
        self.float_deck.clear()
        self.cid = None

    @staticmethod
    def _plot_frame(frame: np.ndarray, 
                    xax: str="frame xax", yax = "frame yax")->None:
        assert np.issubdtype(frame.dtype, float), "heatmap frame can only be float!"
        colorbar="frame colorbar"
        _fmin, _fmax, (_nVrows, _nHcols) = frame.min(), frame.max(), frame.shape
        if dpg.get_value("manual scale checkbox"):
            _fmin, _fmax, *_ = dpg.get_value("color scale lims")
        dpg.configure_item(
            colorbar, 
            min_scale = _fmin, 
            max_scale = _fmax)
        dpg.delete_item(yax, children_only=True) # this is necessary!
        dpg.add_heat_series(frame, _nVrows, _nHcols, parent=yax, 
                            scale_min=_fmin, scale_max=_fmax,format="",
                            bounds_min= (0,_nVrows), bounds_max= (_nHcols, 0))
        if not dpg.get_item_user_data("frame plot"): # 只有在无 query rect 选区时，才重置 heatmap 的 zoom
            dpg.fit_axis_data(yax)
            dpg.fit_axis_data(xax)
    def plot_avg_frame(self):
        if  self.float_deck:
            avg_frame = sum(self.float_deck) / len(self.float_deck)
            self._plot_frame(avg_frame)
    def plot_cid_frame(self, xax = "frame xax", yax= "frame yax"):
        """
        x/yax kwargs make it possible to plot else where when needed
        """
        if self.cid is not None:
            frame = self.float_deck[self.cid]
            self._plot_frame(frame, xax, yax)
    def plot_frame_dwim(self):
        if dpg.get_value("toggle 积分/单张 map"):
            self.plot_avg_frame()
        else:
            self.plot_cid_frame()

class MyPath(Path):
    def is_readable(self):
        return os.access(self, os.R_OK)
    def is_writable(self):
        return os.access(self, os.W_OK)
    def is_executable(self):
        return os.access(self, os.X_OK)

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
    
def start_flag_watching_acq(
    cam: DCAM.DCAM.DCAMCamera,
    flag: threading.Event,
    frame_deck: FrameDeck,
    controller # type is DDSRampController, not hinted because it acts funny on macOS
    )-> None:
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"]
    awg_params = _collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame = cam.read_oldest_image()
        if awg_is_on:
            feed_AWG(this_frame, controller, awg_params) # feed original uint16 format to AWG
        frame_deck.append(this_frame)
        frame_deck.plot_frame_dwim()
        hLhRvLvR = dpg.get_item_user_data("frame plot")
        if hLhRvLvR:
            _update_hist(hLhRvLvR, frame_deck)
        # print("frame acquired")

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
    print("AWG is opened")
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
    user_tgt_arr_input = dpg.get_value("binary target array")
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

def push_log(msg:str, *, is_error = False):
    """
    TODO: add a visual bell background blinking upon error
    """
    tagWin = "log window"
    dpg.add_text(msg, parent= tagWin, color = (255,0,0) if is_error else None)
    dpg.set_y_scroll(tagWin, dpg.get_y_scroll_max(tagWin))
