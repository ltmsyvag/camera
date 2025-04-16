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
import os
# import deprecated

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

def extend_dpg_methods(m: ModuleType):
    """
    由于 dearpygui 的设计原因，对 GUI 元素的操作都需要在 dpg.create_context() 之后才能使用.
    本"模组装饰器"用于装饰 dpg 模组, 使将很多 gui 元素操作的方法得以用 dpg.method() 的形式执行.
    这不但简化了主脚本中 import 的内容(只 import 一个本装饰器即可), 
    也可以提醒我在 dpg.create_context() 之后才能使用这些附加方法.
    """
    assert m is dpg, "decoratee must be dpg"
    
    def bind_custom_theming():
        with m.theme() as global_theme:
            with m.theme_component(m.mvAll): # online doc: theme components must have a specified item type. This can either be `mvAll` for all items or a specific item type
                # m.add_theme_style(m.mvStyleVar_FrameBorderSize, 1, 
                #                     category=m.mvThemeCat_Core # online docstring paraphrase: you are mvThemeCat_core, if you are not doing plots or nodes. 实际上我发现不加这个 kwarg 也能产生出想要的 theme。但是看到网上都加，也就跟着加吧
                #                     )
                m.add_theme_color(m.mvThemeCol_CheckMark, (255,255,0), category=m.mvThemeCat_Core)
                m.add_theme_style(m.mvStyleVar_FrameRounding, 3, category=m.mvThemeCat_Core)
        m.bind_theme(global_theme)
    

    def initialize_chinese_fonts(default_fontsize: int=19, 
                        bold_fontsize: int=21, 
                        large_fontsize: int=30) -> tuple[int, int, int]:
        """
        设置一些支持中文的字体和字号, 然后全局绑定一个默认中文字体
        （必须放置在 `dpg.create_context()` 之后）
        see https://dearpygui.readthedocs.io/en/latest/documentation/fonts.html
        """
        def _chinese_font_path() -> tuple[str, str]:
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
                r"/Users/haiteng/Library/Fonts/NotoSansSC-Medium.ttf", # 没有中文字体, 但是读文档舒服
                r"/Users/haiteng/Library/Fonts/NotoSansSC-Bold.ttf", # 没有中文字体, 但是读文档舒服
                ) 
            # elif system == "Darwin": return r"/Users/haiteng/Library/Fonts/sarasa-term-sc-nerd.ttc"
            else: raise NameError("没有定义本操作系统的中文字体地址")
        normal_font_path, large_font_path = _chinese_font_path()
        bold_font_path = large_font_path
        with m.font_registry():
            with m.font(normal_font_path, default_fontsize) as default_font:
                # m.add_font_range_hint(m.mvFontRangeHint_Chinese_Simplified_Common) # 不包含锶铷这类生僻字
                m.add_font_range_hint(m.mvFontRangeHint_Chinese_Full)
            with m.font(bold_font_path, bold_fontsize) as bold_font:
                m.add_font_range_hint(m.mvFontRangeHint_Chinese_Full)
            with m.font(large_font_path, large_fontsize) as large_font:
                m.add_font_range_hint(m.mvFontRangeHint_Chinese_Full)
        m.bind_font(default_font)
        return default_font, bold_font, large_font
    def initialize_toggle_btn():
        """
        因为准备 toggle button 一定有两个条件: 1. 装饰 pdg.add_button. 2. 装饰 toggle button 的 callback.
        因此本方法内部执行第一步, 同时返回第二步所需的 decor, 非常合理. 在执行上表示这两个 explicit 的步骤缺一不可.
        另一方面, 如果我在某个项目中完全不打算使用 toggle button. 那么本方法不会被 call, 也就不会创造出第二步的 decor,
        满足"如无必要, 勿增实体"的逻辑.
        """
        _off_rgb = (202, 33, 33) # off rgb 
        _offhov_rgb = (255, 0, 0) # off hovered rgb
        _on_rgb = (25,219,72) # on rgb 
        _onhov_rgb = (0,255,0) # on hovered rgb 
        _1 = 15 # frame rounding
        with m.theme() as theme_btnoff:
            with m.theme_component(m.mvAll):
                m.add_theme_color(m.mvThemeCol_Button, _off_rgb, category=m.mvThemeCat_Core)
                m.add_theme_color(m.mvThemeCol_ButtonHovered, _offhov_rgb, category=m.mvThemeCat_Core)
                m.add_theme_color(m.mvThemeCol_ButtonActive, _offhov_rgb, category=m.mvThemeCat_Core)
                # m.add_theme_color(m.mvThemeCol_Text, rgbOppositeTo(*_off_rgb), category=m.mvThemeCat_Core) 
                m.add_theme_style(m.mvStyleVar_FrameRounding, _1, category=m.mvThemeCat_Core)
        with m.theme() as theme_btnon:
            with m.theme_component(m.mvAll):
                m.add_theme_color(m.mvThemeCol_Button, _on_rgb, category=m.mvThemeCat_Core)
                m.add_theme_color(m.mvThemeCol_ButtonHovered, _onhov_rgb, category=m.mvThemeCat_Core)
                m.add_theme_color(m.mvThemeCol_ButtonActive, _onhov_rgb, category=m.mvThemeCat_Core)
                m.add_theme_color(m.mvThemeCol_Text, rgb_opposite(*_on_rgb), category=m.mvThemeCat_Core) 
                m.add_theme_style(m.mvStyleVar_FrameRounding, _1, category=m.mvThemeCat_Core)

        def _provide_toggle_btn_mechanism(func):
            """
            dpg.add_button 的装饰器, 使该命令可以创造初始化的 themed toggle button
            """
            assert func is m.add_button, "decoratee must be dearpygui.dearpygui.add_button"
            def wrapper(*args, **kwargs):
                btn = func(*args, **kwargs)
                if "user_data" in kwargs:
                    if isinstance(kwargs["user_data"], dict):
                        _dict = kwargs["user_data"]
                        if "is on" in _dict:
                            if _dict["is on"]:
                                m.bind_item_theme(btn, theme_btnon)
                                if "on label" in _dict:
                                    m.set_item_label(btn, _dict["on label"])
                            else:
                                m.bind_item_theme(btn, theme_btnoff)
                                if "off label" in _dict:
                                    m.set_item_label(btn, _dict["off label"])
                return btn
            return wrapper
        m.add_button = _provide_toggle_btn_mechanism(m.add_button) # 装饰 add_button 命令
        def toggle_btn_state_and_disable_items(*items, on_and_enable=True):
            """
            搭配 toggle button 使用的装饰器. 本函数是母函数 initialize_toggle_btn 的返回.
            也就是说, 如果在一个不用 toggle button 的项目中, initialize_toggle_btn 不会被 call, 
            那么本函数永远不会被创建. 
            本装饰器用于装饰 toggle button 的 callback. 它的作用包括:
            1. 根据 user_data 中的 "is on" key 判断 toggle 状态, 从而切换 button 的 on/off theme 和 label
            2. 在 callback 执行失败时, 用 button label 报错
                TODO 设置一个 button tooltip 来给出详细错误信息
            3. 在 callback 执行成功后, 修改 user_data["is on"] 所保存的 toggle 状态.
            4. 在 toggle on/off 成功时，enable/disable (若 `on_and_enable=False` 
               则是 disable/enable) 参数 items 中包含的 gui 元素.
            """
            def middle(cb):
                def wrapper(sender, app_data, user_data):
                    assert m.get_item_type(sender) == "mvAppItemType::mvButton", "sender must be a button"
                    assert isinstance(user_data, dict) and ("is on" in user_data), "user_data must be a dict with 'is on' key"
                    state = user_data["is on"]
                    next_state = not state
                    if next_state:
                        m.set_item_label(sender, "开启中…")
                    else:
                        m.set_item_label(sender, "关闭中…")
                    try:
                        cb(sender, app_data, user_data)
                        state = not state # flip state
                        for item in items:
                            m.configure_item(item, enabled=state if on_and_enable else not state)
                    except Exception as e:
                        m.set_item_label(sender, "错误!")
                        print("exception type: ", type(e).__name__)
                        print("exception message: ", e)
                        return # exit early 

                    if state:
                        m.bind_item_theme(sender, theme_btnon)
                        label = user_data["on label"] if "on label" in user_data else ""
                        m.set_item_label(sender, label)
                    else:
                        m.bind_item_theme(sender, theme_btnoff)
                        label = user_data["off label"] if "off label" in user_data else ""
                        m.set_item_label(sender, label)
                    user_data["is on"] = state
                    m.set_item_user_data(sender, user_data) # store state
                return wrapper
            return middle
        return toggle_btn_state_and_disable_items
    m.initialize_toggle_btn = initialize_toggle_btn
    m.initialize_chinese_fonts = initialize_chinese_fonts
    m.bind_custom_theming = bind_custom_theming
    return m

if __name__ == "__main__":
    frame = _my_rand_frame(240, 240)
    notsaved = save_with_timestamp(r"", frame)