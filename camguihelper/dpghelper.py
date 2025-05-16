#%%
"""
dpg 相关的帮助函数, 主要用于个人初始化和 batch processing
"""
import traceback
import platform
from .core import rgb_opposite, push_exception
import dearpygui.dearpygui as dpg
from typing import Callable
def _do_fix_disabled_components()->None:
    """
    used under a `with dpg.theme()` context.

    this code is from https://github.com/hoffstadt/DearPyGui/issues/2068. 
    What it does is binding disabled theme colors for texts separately depending on the item type. 
    Because a simple dpg.mvAll does not work (it should) due to bug.
    """
    for comp_type in ( # 
        dpg.mvMenuItem, dpg.mvButton, dpg.mvText,
        dpg.mvDragIntMulti,
        dpg.mvInputInt, dpg.mvInputIntMulti, 
        dpg.mvInputDouble, dpg.mvInputDoubleMulti,
        dpg.mvInputFloat, dpg.mvInputFloatMulti,
        dpg.mvInputText, dpg.mvCheckbox):
        with dpg.theme_component(comp_type, enabled_state=False):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (0.50 * 255, 0.50 * 255, 0.50 * 255, 1.00 * 255), category=dpg.mvThemeCat_Core)
    with dpg.theme_component(dpg.mvRadioButton, enabled_state=False):
        dpg.add_theme_color(# if you put this setting into the comp_type forloop, it won't work. probably because this radio_button-exclusive component will override
            dpg.mvThemeCol_Text, (0.50 * 255, 0.50 * 255, 0.50 * 255, 1.00 * 255), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(# the checkmark controls the color of the selected radio button
            dpg.mvThemeCol_CheckMark, (0.50 * 255, 0.50 * 255, 0.50 * 255, 1.00 * 255), category=dpg.mvThemeCat_Core)

def do_bind_my_global_theme()->None:
    with dpg.theme() as global_theme:
        _do_fix_disabled_components()
        with dpg.theme_component(dpg.mvAll): # check mark is distinc yellow. dpg.mvCheckbox doesn't work, don't know why
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (255,255,0), category=dpg.mvThemeCat_Core)
            # dpg.add_theme_color(dpg.mvThemeCol_DockingEmptyBg, (0,0,0, 255), category=dpg.mvThemeCat_Core) # 在 docking_space 开启时, 尝试将其变为黑色. doesn't work, don't know why.
        with dpg.theme_component(dpg.mvButton): # my button style, a bit roundish with magenta border, with distinct blueish color when pressed down
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (255,0,255,200), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0,119,200), category=dpg.mvThemeCat_Core)
        with dpg.theme_component(dpg.mvInputInt): # input field 带有 +/- 按钮时, 也希望点击的时候按钮的 active 状态能更有辨识度. 由于 input field 自带的按钮不属于 mvButton, 需要单独设置一次
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0,119,200), category=dpg.mvThemeCat_Core)
        for comp in (dpg.mvInputInt, dpg.mvInputIntMulti, 
                     dpg.mvInputDouble, dpg.mvInputDoubleMulti,
                     dpg.mvInputFloat, dpg.mvInputFloatMulti,
                     dpg.mvInputText, dpg.mvCheckbox): # give frame borders in all kinds of input fields
            with dpg.theme_component(comp):
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0.5, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Border, (255,255,255,25), category=dpg.mvThemeCat_Core)
    dpg.bind_theme(global_theme)
    

def do_initialize_chinese_fonts(default_fontsize: int=19, 
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
        elif system == "Darwin": return ( # google noto
            r"/Users/haiteng/Library/Fonts/NotoSansSC-Medium.ttf",
            r"/Users/haiteng/Library/Fonts/NotoSansSC-Bold.ttf", 
            ) 
        else: raise NameError("没有定义本操作系统的中文字体地址")
    normal_font_path, large_font_path = _chinese_font_path()
    bold_font_path = large_font_path
    with dpg.font_registry():
        with dpg.font(normal_font_path, default_fontsize) as default_font:
            # dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common) # 不包含锶铷这类生僻字
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
        with dpg.font(bold_font_path, bold_fontsize) as bold_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
        with dpg.font(large_font_path, large_fontsize) as large_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
    dpg.bind_font(default_font)
    return default_font, bold_font, large_font

def do_extend_add_button() -> Callable:
    """
    implicit decoration for dpg.add_button
    不止一个装饰, 下面仅讲解一下做出 toggle button 的相关装饰.
    因为准备 toggle button 一定有两个条件: 1. 装饰 pdg.add_button. 2. 装饰 toggle button 的 callback.
    因此本方法内部执行第一步, 同时返回第二步所需的 decor, 非常合理. 在执行上表示这两个 explicit 的步骤缺一不可.
    另一方面, 如果我在某个项目中完全不打算使用 toggle button. 那么函数不会被 call, 也就不会创造出第二步的 decor,
    满足"如无必要, 勿增实体"的逻辑.
    """
    _rgb_tog_off = (202, 33, 33) # off rgb 
    _rgb_tog_offhov = (255, 0, 0) # off hovered rgb
    _rgb_tog_on = (25,219,72) # on rgb 
    _rgb_tog_onhov = (0,255,0) # on hovered rgb 
    _1 = 15 # frame rounding
    def _do_add_invar_toggle_styles()->None:
        """
        userd under `with dpg.theme_component()` context
        invariant button styles/colors independent from toggle states or active states
        """
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, category=dpg.mvThemeCat_Core) # 全局按钮设置了 border, 但是 toggle 按钮我不想要, 因此进行 local override
        # dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1, -1, category=dpg.mvThemeCat_Core)
    def _do_config_disabled_toggle_components()->None:
        """
        used under `with dpg.theme()` context
        """
        with dpg.theme_component(dpg.mvButton, enabled_state=False):
            _do_add_invar_toggle_styles()
    with dpg.theme() as theme_toggle_off:
        _do_config_disabled_toggle_components()
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, _rgb_tog_off, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _rgb_tog_offhov, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _rgb_tog_off, category=dpg.mvThemeCat_Core)
            # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_off_rgb), category=dpg.mvThemeCat_Core) 
            _do_add_invar_toggle_styles()
    with dpg.theme() as theme_toggle_on:
        _do_config_disabled_toggle_components()
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, _rgb_tog_on, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _rgb_tog_onhov, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _rgb_tog_on, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Text, rgb_opposite(*_rgb_tog_on), category=dpg.mvThemeCat_Core) 
            _do_add_invar_toggle_styles()
    ## 以下定义在本 do 函数之内的 decor 都不用 explicitly 命名为 decor_add_button, 因为它们装饰 dpg.add_button 的行为是固定在 do 函数定义中的, 不会在外部使用
    def _decor_bind_comfy_btn_framepadding_wo_widhite_kwargs(func: Callable)->Callable:
        """
        dpg.add_button 的装饰器
        在运行 dpg.add_button 但是不指定 kwargs `width` 和 `height` 时, 使用比默认值大一些的 frame padding. 默认值太小了
        这个设置原则上可以放在 global theme 里, 但是实验发现放在 dpg.add_button 的 decor 里是最好的
        """
        def wrapper(*args, **kwargs):
            tagBtn = func(*args, **kwargs)
            if ("width" not in kwargs) and ("height" not in kwargs):
                with dpg.theme() as theme_no_framepadding:
                    _pad_comfy_x, _pad_comfy_y = 10, 5
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, _pad_comfy_x, _pad_comfy_y, category=dpg.mvThemeCat_Core)
                    with dpg.theme_component(dpg.mvButton, enabled_state=False):
                        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, _pad_comfy_x, _pad_comfy_y, category=dpg.mvThemeCat_Core)
                dpg.bind_item_theme(tagBtn, theme_no_framepadding)
            return tagBtn
        return wrapper
    def _decor_bind_toggle_theme_upon_ison_usritem(func: Callable)->Callable:
        """
        dpg.add_button 的装饰器, 使该命令可以创造初始化的 themed toggle button
        """
        def wrapper(*args, **kwargs) -> int:
            tagBtn = func(*args, **kwargs)
            if "user_data" in kwargs:
                if isinstance(kwargs["user_data"], dict):
                    _dict = kwargs["user_data"]
                    if "is on" in _dict:
                        if _dict["is on"]:
                            dpg.bind_item_theme(tagBtn, theme_toggle_on)
                            if "on label" in _dict:
                                dpg.set_item_label(tagBtn, _dict["on label"])
                        else:
                            dpg.bind_item_theme(tagBtn, theme_toggle_off)
                            if "off label" in _dict:
                                dpg.set_item_label(tagBtn, _dict["off label"])
            return tagBtn
        return wrapper # _return_func_if_not_wrapped(func,wrapper)
    dpg.add_button = _decor_bind_comfy_btn_framepadding_wo_widhite_kwargs(dpg.add_button)
    dpg.add_button = _decor_bind_toggle_theme_upon_ison_usritem(dpg.add_button) # 装饰 add_button 命令

    def toggle_btn_state_and_disable_items(*items, on_and_enable=True)->Callable:
        """
        搭配 toggle button 使用的装饰器. 本函数是母函数 initialize_toggle_btn 的返回.
        也就是说, 如果在一个不用 toggle button 的项目中, initialize_toggle_btn 不会被 call, 
        那么本函数永远不会被创建. 
        本装饰器用于装饰 toggle button 的 callback. 它的作用包括:
        1. 根据 user_data 中的 "is on" key 判断 toggle 状态, 从而切换 button 的 on/off theme 和 label
        2. 在 callback 执行失败时, 用 button label 报错
        3. 在 callback 执行成功后, 修改 user_data["is on"] 所保存的 toggle 状态.
        4. 在 toggle on/off 成功时，enable/disable (若 `on_and_enable=False` 
            则是 disable/enable) 参数 items 中包含的 gui 元素.
        """
        def decor(cb)->None:
            def wrapper(sender, app_data, user_data):
                assert dpg.get_item_type(sender) == "mvAppItemType::mvButton", "sender must be a button"
                assert isinstance(user_data, dict) and ("is on" in user_data), "user_data must be a dict with 'is on' key"
                state = user_data["is on"]
                next_state = not state
                if next_state:
                    dpg.set_item_label(sender, "开启中…")
                else:
                    dpg.set_item_label(sender, "关闭中…")
                try:
                    cb(sender, app_data, user_data)
                    state = not state # flip state
                    for item in items:
                        dpg.configure_item(item, enabled=state if on_and_enable else not state)
                except Exception:
                    dpg.set_item_label(sender, "错误!")
                    push_exception("相机错误")
                    return

                if state:
                    dpg.bind_item_theme(sender, theme_toggle_on)
                    label = user_data["on label"] if "on label" in user_data else ""
                    dpg.set_item_label(sender, label)
                else:
                    dpg.bind_item_theme(sender, theme_toggle_off)
                    label = user_data["off label"] if "off label" in user_data else ""
                    dpg.set_item_label(sender, label)
                user_data["is on"] = state
                dpg.set_item_user_data(sender, user_data) # store state
            return wrapper
        return decor
    return toggle_btn_state_and_disable_items

def toggle_checkbox_and_disable(*items, on_and_enable=False):
    """
    这个函数和上面的 toggle_btn_state_and_disable_items 类似,
    但之所以要独立定义本函数, 是因为 checkbox 的 toggle state boolean
    是 app_data, 是用户无法介入控制的: 每次点击必然会 flip state,
    即使 callback 执行报错, 也会 flip state.
    也就是说这个 app_data boolean 反映的就是 checkbox 在点击后必然会变化的
    cosmetic change.
    因此, toggle button (由于可以在报错时即时决定 state boolean 和 button 外观)
    适合用于 volatile 的仪器状态 toggle. 
    而 checkbox 适合用于必然可以无意外 toggle 的对象. 
    """
    def decor(cb):
        def wrapper(_, app_data, __):
            cb(_, app_data, __)
            for item in items:
                dpg.configure_item(item, enabled=app_data if on_and_enable else not app_data)
        return wrapper
    return decor


def _return_func_if_not_wrapped(func, wrapper):
    """
    update1: 貌似没啥卵用
    decor 定义专用函数. 可以避免 rerun script 时的二次 wrapping (否则只能一次次重启 kernel)
    用法: 删掉 decor 定义尾部的 `return wrapper`, 改为 `_return_func_if_not_wrapped(func, wrapper)`.
    # 本函数在未 `func` 和 `wrapper` 来命名形参和返回值. 最终让本函数决定返回哪一个.
    """
    if not getattr(func, "_is_decorated", False):
        wrapper._is_decorated = True
        return wrapper
    else:
        return func

def _get_viewport_centerpos():
    center_x = dpg.get_viewport_client_width()//2
    center_y = dpg.get_viewport_client_height()//2
    return center_x, center_y

def factory_cb_yn_modal_dialog(*, cb_on_confirm: Callable = None, 
                               cb_on_cancel: Callable = None, 
                               dialog_text: str = "确认吗?",
                               win_label: str = "确认操作",
                               just_close : bool=False # just pop a window that shows a message. you close the window by clicking the top right "x"
                               ) -> Callable:
    """
    factory generating a callback producing a yes/no modal dialog window
    """
    tagModalWin = dpg.generate_uuid()
    def _cb_on_cancel():
        dpg.delete_item(tagModalWin)  # Close the modal after cancelling
    def pop_yn_modal_win():
        with dpg.window(label = win_label, modal = True, tag = tagModalWin,
                        pos = _get_viewport_centerpos(), 
                        on_close=lambda sender: dpg.delete_item(sender)):
            dpg.add_text(dialog_text)
            if just_close:
                pass
            else:
                dpg.add_spacer(height=10)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=30)
                    dpg.add_button(label = "Yes", callback = cb_on_confirm)
                    dpg.add_button(label = "No", callback = cb_on_cancel if cb_on_cancel else _cb_on_cancel)
    return pop_yn_modal_win