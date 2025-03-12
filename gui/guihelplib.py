#%%
import platform
import threading
from types import ModuleType # 用于 type annotation
# import dearpygui.dearpygui as dpg
from pylablib.devices import DCAM
import numpy as np
import dearpygui.dearpygui as dpg


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

def plotFrame(frame: np.ndarray,
              ax = "frame yax",
              colorbar="frame colorbar",
              ) -> None:
    fframe, _fmin, _fmax, (_nVrows, _nHcols) = frame.astype(float), frame.min(), frame.max(), frame.shape
    if dpg.get_value("manual scale checkbox"):
        _fmin, _fmax, *_ = dpg.get_value("color scale lims")
    dpg.configure_item(
        colorbar, 
        min_scale = _fmin, 
        max_scale = _fmax)
    dpg.delete_item(ax, children_only=True) # this is necessary!
    dpg.add_heat_series(fframe, _nVrows, _nHcols, parent=ax, 
                        scale_min=_fmin, scale_max=_fmax,format="",
                        bounds_min= (1,1), bounds_max= (_nHcols, _nVrows))
    dpg.fit_axis_data(ax)
    dpg.fit_axis_data("frame xax")

def storeAndPlotFrame(frame: np.ndarray, frameStack: list)-> None:
    frameStack.append(frame)
    # if len(frameStack) > 500: frameStack.pop(0)
    dpg.set_item_user_data("plot previous frame", len(frameStack)-1)
    dpg.set_value("frame stack count display", f"{len(frameStack)} frames in stack")
    plotFrame(frame)
    # fframe, _fmin, _fmax, (_nVrows, _nHcols) = frame.astype(float), frame.min(), frame.max(), frame.shape
    # dpg.configure_item(colorbar, min_scale =_fmin, max_scale=_fmax)
    # dpg.delete_item(ax, children_only=True) # this is necessary!
    # dpg.add_heat_series(fframe, _nVrows, _nHcols, parent=ax, 
    #                     scale_min=_fmin, scale_max=_fmax,format="",
    #                     bounds_min= (1,1), bounds_max= (_nHcols, _nVrows))
    # dpg.fit_axis_data(ax)
    # dpg.fit_axis_data("frame xax")

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
        _feedTheAWG(thisFrame)
        storeAndPlotFrame(thisFrame, frameStack)
        print("frame acquired")



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

def _setChineseFont(dpg: ModuleType,
                    default_fontsize: int, 
                    bold_fontsize: int, 
                    large_fontsize: int) -> tuple[int, int]:
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


import colorsys
def rgbOppositeTo(r, g, b):
    """
    给出某 rgb 相对最大对比度颜色（HSL approach）。@GPT
    """
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255) # convert to HSL
    h = (h + 0.5) % 1.0 # Rotate hue by 180° (opposite color)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s) # Convert back to RGB
    return int(r2*255), int(g2*255), int(b2*255)

