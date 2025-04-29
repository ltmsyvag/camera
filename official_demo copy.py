#%%
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from camguihelper.dpghelper import *

dpg.create_context()
do_bind_my_global_theme()
do_initialize_chinese_fonts(20)
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

with dpg.theme() as theme_framepadding:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,10, 10, category=dpg.mvThemeCat_Core)
    with dpg.theme_component(dpg.mvAll, enabled_state=False):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,10, 10, category=dpg.mvThemeCat_Core)

# dpg.bind_theme(theme_framepadding)


with dpg.theme() as theme_no_framepadding:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1,-1, category=dpg.mvThemeCat_Core)
    with dpg.theme_component(dpg.mvButton, enabled_state=False):
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1,-1,category=dpg.mvThemeCat_Core)
def _decor_bind_zero_frame_padding_upon_wid_hite_kwargs(func):
    """
    手动设置 width, height 的按钮中的 label 文字的周围留白大小不是按照 dpg.mvStyleVar_FramePadding 来的, 
    如果此时还保有全局默认的 frame padding, 则会让按钮 label 的 justifucation 变得不居中, 看起来很奇怪
    """
    def wrapper(*args, **kwargs):
        btn = func(*args, **kwargs)
        if ("width" in kwargs) or ("height" in kwargs):
            
            dpg.bind_item_theme(btn, theme_no_framepadding)
    return wrapper

_off_rgb = (202, 33, 33) # off rgb 
_offhov_rgb = (255, 0, 0) # off hovered rgb
_on_rgb = (25,219,72) # on rgb 
_onhov_rgb = (0,255,0) # on hovered rgb 
_1 = 15 # frame rounding
def _container():
    dpg.add_theme_color(dpg.mvThemeCol_Button, _off_rgb, category=dpg.mvThemeCat_Core)
    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _offhov_rgb, category=dpg.mvThemeCat_Core)
    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _off_rgb, category=dpg.mvThemeCat_Core)
    # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_off_rgb), category=dpg.mvThemeCat_Core) 
    dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)
    dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, category=dpg.mvThemeCat_Core) # 全局按钮设置了 border, 但是 toggle 按钮我不想要, 因此进行 local override
def _disabled_theming():
    for comp_type in ( # this code is from https://github.com/hoffstadt/DearPyGui/issues/2068. What it does is binding disabled theme colors for texts separately depending on the item type. Because a simple dpg.mvAll does not work (it should) due to bug.
        dpg.mvMenuItem, dpg.mvButton, dpg.mvText):
        with dpg.theme_component(comp_type, enabled_state=False):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (0.50 * 255, 0.50 * 255, 0.50 * 255, 1.00 * 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, category=dpg.mvThemeCat_Core)
with dpg.theme() as theme_btnoff:
    with dpg.theme_component(dpg.mvAll):
        _container()
        # dpg.add_theme_color(dpg.mvThemeCol_Button, _off_rgb, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _offhov_rgb, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _off_rgb, category=dpg.mvThemeCat_Core)
        # # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_off_rgb), category=dpg.mvThemeCat_Core) 
        # dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, category=dpg.mvThemeCat_Core) # 全局按钮设置了 border, 但是 toggle 按钮我不想要, 因此进行 local override
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1,-1, category=dpg.mvThemeCat_Core)
    _disabled_theming()
with dpg.theme() as theme_btnon:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _on_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _onhov_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _on_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_Text, rgb_opposite(*_on_rgb), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0, category=dpg.mvThemeCat_Core) # 全局按钮设置了 border, 但是 toggle 按钮我不想要, 因此进行 local override
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding,-1,-1, category=dpg.mvThemeCat_Core)
    _disabled_theming()
def _decor_bind_toggle_theme_upon_ison_usritem(func):
    """
    dpg.add_button 的装饰器, 使该命令可以创造初始化的 themed toggle button
    """
    # assert func is dpg.add_button, "decoratee must be dearpygui.dearpygui.add_button"
    def wrapper(*args, **kwargs):
        tagBtn = func(*args, **kwargs)
        if "user_data" in kwargs:
            if isinstance(kwargs["user_data"], dict):
                _dict = kwargs["user_data"]
                if "is on" in _dict:
                    if _dict["is on"]:
                        dpg.bind_item_theme(tagBtn, theme_btnon)
                        if "on label" in _dict:
                            dpg.set_item_label(tagBtn, _dict["on label"])
                    else:
                        dpg.bind_item_theme(tagBtn, theme_btnoff)
                        if "off label" in _dict:
                            dpg.set_item_label(tagBtn, _dict["off label"])
        return tagBtn
    return wrapper # _return_func_if_not_wrapped(func,wrapper)
dpg.add_button = _decor_bind_toggle_theme_upon_ison_usritem(dpg.add_button)
# dpg.add_button = _decor_bind_zero_frame_padding_upon_wid_hite_kwargs(dpg.add_button)

with dpg.window():
    btn = dpg.add_button(label="中文", 
                   width = 150, 
                   height = 35,
                   user_data = {"is on": False}, enabled=False
                   )
    # dpg.bind_item_theme(btn, theme_no_framepadding)
    dpg.add_input_text(label = "hello world")

# demo.show_demo()
# dpg.show_style_editor()


dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
