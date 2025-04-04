#%%
import math
from datetime import datetime
from pathlib import Path
import platform
import threading
from types import ModuleType # 用于 type annotation
from pylablib.devices import DCAM
import numpy as np
import dearpygui.dearpygui as dpg
import colorsys
import tifffile

class FrameStack(list):
    """
    a method to be developed.
    """
    cid = None # current heatmap's id in stack # unused yet
    def getAvgFrame(self):
        """
        why don't I simply use `sum(mylist)`? becaue `sum(<empty list []>)` returns 0, 
        whereas in the case of a frame stack list, it should return None when there's no frame.
        So this method is better!
        """
        if self: # non empty list
            return sum(self)
def _feedTheAWG(frame):
    pass
def _myRandFrame(v=2304,h=4096, max=65535)-> np.ndarray:
    myarr = np.random.randint(0,max, size = v*h, dtype=np.uint16)
    return myarr.reshape((v,-1))

def guiOpenCam() -> DCAM.DCAM.DCAMCamera:
    cam = DCAM.DCAMCamera()
    if cam.is_opened(): cam.close()
    cam.open()
    print("cam is opened")
    return cam

def ZYLconversion(frame: np.ndarray)->np.ndarray:
    """
    ZYL formula to infer photon counts
    """
    frame = (frame -200) * 0.1/0.9
    return frame
def plotFrame(frame: np.ndarray,
              yax = "frame yax",
              colorbar="frame colorbar",
              ) -> None:
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

def storeAndPlotFrame(frame: np.ndarray, frameStack: FrameStack)-> None:
    frameStack.append(frame)
    # if len(frameStack) > 500: frameStack.pop(0)
    dpg.set_item_user_data("plot previous frame", len(frameStack)-1)
    dpg.set_value("frame stack count display", f"{len(frameStack)} frames in stack")
    if dpg.get_value("toggle 积分/单张 map"):
        plotFrame(frameStack.getAvgFrame())
    else:
        plotFrame(frame)

def _updateHist(hLhRvLvR: tuple, frameStack:list, yax = "hist plot yax")->None:
    """
    hLhRvLvR 保存了一个矩形选区所包裹的像素中心点坐标（只能是半整数）h 向最小最大值和 v 向最小最大值。
    这些值确定了所选取的像素集合。然后，在此选择基础上将 frame stack 中的每一张 frame 在该选区中的部分的 counts 求得，
    加入 histdata 数据列表
    """
    hLlim, hRlim, vLlim, vRlim = hLhRvLvR
    vidLo, vidHi = math.floor(vLlim), math.floor(vRlim)
    hidLo, hidHi = math.floor(hLlim), math.floor(hRlim)
    histData = []
    for frame in frameStack: # make hist data
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

def startAcqLoop(
        cam: DCAM.DCAM.DCAMCamera,
        event: threading.Event,
        frameStack: list)-> None:
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    while event.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        thisFrame = cam.read_oldest_image()
        _feedTheAWG(thisFrame) # feed original uint16 format to AWG
        storeAndPlotFrame(thisFrame.astype(float), frameStack) # I changed the default uint16 type when I acquire each frame. I need float (not uint16) for robust graphic processing, and batch conversion of many frames to int can be slow (e.g. when plotting the avg frame) for large frame stack.
        hLhRvLvR = dpg.get_item_user_data("frame plot")
        if hLhRvLvR:
            _updateHist(hLhRvLvR, frameStack)
        # print("frame acquired")



def _chinesefontpath() -> str:
    """
    返回中文字体地址，以便 dpg 调用
    返回 tuple (normalFontPath, largeFontPath)
    """
    system = platform.system()
    if system == "Windows": 
        return (
            r"C:/Windows/Fonts/msyh.ttc", # 微软雅黑
            r"C:/Windows/Fonts/msyhbd.ttc", # 微软雅黑 bold
                ) # 微软雅黑 bold
    # elif system == "Darwin": return r"/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    elif system == "Darwin": return (
        r"/System/Library/Fonts/Monaco.ttf", # 没有中文字体, 但是读文档舒服
        r"/System/Library/Fonts/Monaco.ttf", # 没有中文字体, 但是读文档舒服
        ) 
    # elif system == "Darwin": return r"/Users/haiteng/Library/Fonts/sarasa-term-sc-nerd.ttc"
    else: raise NameError("没有定义本操作系统的中文字体地址")

def _setChineseFont(default_fontsize: int, 
                    bold_fontsize: int=21, 
                    large_fontsize: int=30) -> tuple[int, int]:
    """
    设置一些支持中文的字体和字号, 然后全局绑定一个默认中文字体
    （必须放置在 `dpg.create_context()` 之后）
    see https://dearpygui.readthedocs.io/en/latest/documentation/fonts.html
    """
    normalFontPath, largeFontPath = _chinesefontpath()
    boldFontPath = largeFontPath
    with dpg.font_registry():
        with dpg.font(normalFontPath, default_fontsize) as default_font:
            # dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common) # 不包含锶铷这类生僻字
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)  
        with dpg.font(boldFontPath, bold_fontsize) as bold_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
        with dpg.font(largeFontPath, large_fontsize) as large_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(default_font)
    return default_font, bold_font, large_font



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



def rgbOppositeTo(r, g, b):
    """
    给出某 rgb 相对最大对比度颜色（HSL approach）。@GPT
    """
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255) # convert to HSL
    h = (h + 0.5) % 1.0 # Rotate hue by 180° (opposite color)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s) # Convert back to RGB
    return int(r2*255), int(g2*255), int(b2*255)

def saveWithTimestamp(dpathStr: str, frame: np.ndarray, id: int=0) -> bool:
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
if __name__ == "__main__":
    frame = _myRandFrame(240, 240)
    notsaved = saveWithTimestamp(r"", frame)