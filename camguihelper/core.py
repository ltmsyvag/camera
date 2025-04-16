"""
camgui 相关的帮助函数
"""
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

class FrameStack(list):
    """
    class of a special list with my own methods for manipulating the frames it stores
    """
    cid = None # current heatmap's id in stack
    float_stack = [] # gui 中的操作需要 float frame, 因此与 list (int stack) 对应, 要有一个 float stack
    def _update(self):
        """
        强制 float_stack 和与 list 内容同步, overhead 可能较大, 在需要的时候使用
        同时执行:
        - 更新 stack counts 显示
        - 调整 cid 到 stack 最末
        """
        if self:
            self.float_stack = [e.astype(float) for e in self]
            self.cid = len(self) - 1
            dpg.set_value("frame stack count display", f"{len(self)} frames in stack")
            if dpg.get_value("toggle 积分/单张 map"):
                self.plot_avg_frame()
            else:
                self.plot_cid_frame()
    def append(self, frame: np.ndarray):
        """
        append a new frame to int & float stacks
        """
        assert np.issubdtype(frame, np.uint16), "frame should be uint16, something's off?!"

        super().append(frame)
        self.float_stack.append(frame.astype(float))
        self.cid = len(self.float_stack) - 1
        dpg.set_value("frame stack count display", f"{len(self)} frames in stack")
    def clear(self):
        """
        clear int & float stacks
        """
        super().clear()
        self.float_stack.clear()
        self.cid = None

    def _plot_frame(self, frame: np.ndarray):
        assert np.issubdtype(frame.dtype, float), "heatmap frame can only be float!"
        yax = "frame yax"
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
            dpg.fit_axis_data("frame xax")
    def plot_avg_frame(self):
        if  self.float_stack:
            avg_frame = sum(self.float_stack) / len(self.float_stack)
            self._plot_frame(avg_frame)
    def plot_cid_frame(self):
        if self.cid is not None:
            frame = self.float_stack[self.cid]
            self._plot_frame(frame)

class MyPath(Path):
    def is_readable(self):
        return os.access(self, os.R_OK)
    def is_writable(self):
        return os.access(self, os.W_OK)
    def is_executable(self):
        return os.access(self, os.X_OK)

def dummy_feed_awg(frame):
    pass
def _my_rand_frame(v=2304,h=4096, max=65535)-> np.ndarray:
    myarr = np.random.randint(0,max, size = v*h, dtype=np.uint16)
    return myarr.reshape((v,-1))

def gui_open_cam() -> DCAM.DCAM.DCAMCamera:
    cam = DCAM.DCAMCamera()
    if cam.is_opened(): cam.close()
    cam.open()
    print("cam is opened")
    return cam

def ZYLconversion(frame: np.ndarray)->np.ndarray:
    """
    ZYL formula to infer photon counts
    """
    frame = (frame -300) * 0.1/0.9
    return frame

def _update_hist(hLhRvLvR: tuple, frame_stack: FrameStack, yax = "hist plot yax")->None:
    """
    hLhRvLvR 保存了一个矩形选区所包裹的像素中心点坐标（只能是半整数）h 向最小最大值和 v 向最小最大值。
    这些值确定了所选取的像素集合。然后，在此选择基础上将 frame stack 中的每一张 frame 在该选区中的部分的 counts 求得，
    加入 histdata 数据列表
    """
    hLlim, hRlim, vLlim, vRlim = hLhRvLvR
    vidLo, vidHi = math.floor(vLlim), math.floor(vRlim)
    hidLo, hidHi = math.floor(hLlim), math.floor(hRlim)
    histData = []
    for frame in frame_stack.float_stack: # make hist data
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
    
def start_acqloop(
    cam: DCAM.DCAM.DCAMCamera,
    event: threading.Event,
    frame_stack: FrameStack)-> None:
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    while event.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame = cam.read_oldest_image()
        dummy_feed_awg(this_frame) # feed original uint16 format to AWG
        frame_stack.append(this_frame)
        if dpg.get_value("toggle 积分/单张 map"):
            frame_stack.plot_avg_frame()
        else:
            frame_stack.plot_cid_frame()
        # _store_and_plot_frame(this_frame.astype(float), frame_stack) # I changed the default uint16 type when I acquire each frame. I need float (not uint16) for robust graphic processing, and batch conversion of many frames to int can be slow (e.g. when plotting the avg frame) for large frame stack.
        hLhRvLvR = dpg.get_item_user_data("frame plot")
        if hLhRvLvR:
            _update_hist(hLhRvLvR, frame_stack)
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

def save_with_timestamp(dpathStr: str, frame: np.ndarray, id: int=0) -> bool:
    """
    保存 frame 为 tiff 文件，文件名为 fpath 加上时间戳, 如果保存失败（dir 不存在, permission denied, etc.）则返回 True
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        dpath = Path(dpathStr)
        fpath = dpath / (timestamp + f"_{id}.tiff")
        tifffile.imwrite(fpath, frame.astype(np.uint16))
        print(f"frame saved as {fpath}")
    except:
        return True

