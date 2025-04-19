#%%
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from camguihelper.dpghelper import *

dpg.create_context()
do_bind_custom_theme()
do_initialize_chinese_fonts(20)
with dpg.theme() as theme_framepadding:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,10, 10, category=dpg.mvThemeCat_Core)
    with dpg.theme_component(dpg.mvAll, enabled_state=False):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,10, 10, category=dpg.mvThemeCat_Core)

# dpg.bind_theme(theme_framepadding)
with dpg.theme() as theme_no_framepadding:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1,-1, category=dpg.mvThemeCat_Core)
    with dpg.theme_component(dpg.mvAll, enabled_state=False):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1,-1,category=dpg.mvThemeCat_Core)
def double_decor_inhibitor(decor):
    def wrapper(func):
        if not getattr(func, "_is_decorated", False):
            decor._is_decorated = True
            return decor(func)
        else:
            return func
    # return wrapper

# @double_decor_inhibitor
def return_func_if_not_wrapped(func, wrapper):
    if not getattr(func, "_is_decorated", False):
        wrapper._is_decorated = True
        return wrapper
    else:
        return func
def _decor_bind_zero_frame_padding_upon_wid_hite_kwargs(func):
    """
    手动设置 width, height 的按钮中的 label 文字的周围留白大小不是按照 dpg.mvStyleVar_FramePadding 来的, 
    如果此时还保有全局默认的 frame padding, 则会让按钮 label 的 justifucation 变得不居中, 看起来很奇怪
    """
    def wrapper(*args, **kwargs):
        btn = func(*args, **kwargs)
        if ("width" in kwargs) or ("height" in kwargs):
            dpg.bind_item_theme(btn, theme_no_framepadding)
    return return_func_if_not_wrapped(func, wrapper)
# if not getattr(dpg.add_button, "_is_decorated", False):
dpg.add_button = _decor_bind_zero_frame_padding_upon_wid_hite_kwargs(dpg.add_button)

dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

with dpg.window():
    dpg.add_button(label="中文", width = 150, 
                   height = 35
                   )
    dpg.add_input_text(label = "hello world")
# demo.show_demo()
# dpg.show_style_editor()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
