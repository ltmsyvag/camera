#%%
import platform
from types import ModuleType # 用于 type annotation
# import dearpygui.dearpygui as dpg
from pylablib.devices import DCAM

_myRoi = 1352,1352+240,948,948+240
def guiOpenCam() -> DCAM.DCAM.DCAMCamera:
    cam = DCAM.DCAMCamera()
    if cam.is_opened(): cam.close()
    cam.open()
    cam.set_trigger_mode("ext")
    cam.set_exposure(0.1)
    cam.set_roi(*_myRoi)
    cam.setup_acquisition(mode="snap", nframes=100)
    print("cam is opened")
    return cam


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

def _setChineseFont(dpg: ModuleType, default_fontsize: int, large_fontsize: int) -> tuple[int, int]:
    """
    设置一些支持中文的字体和字号, 然后全局绑定一个默认中文字体
    （必须放置在 `dpg.create_context()` 之后）
    see https://dearpygui.readthedocs.io/en/latest/documentation/fonts.html
    """
    normalFontPath, largeFontPath = _chinesefontpath()
    with dpg.font_registry():
        with dpg.font(normalFontPath, default_fontsize) as default_font:
            # dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common) # 不包含锶铷这类生僻字
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)   # @source 这个会影响启动速度
        with dpg.font(largeFontPath, large_fontsize) as large_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(default_font)
    return default_font, large_font



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

if __name__ == "__main__":
    print(chinesefontpath())