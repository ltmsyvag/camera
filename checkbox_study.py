#%%
import dearpygui.dearpygui as dpg

from mydpghelper import extend_dpg_methods, _log, toggle_checkbox_and_disable
dpg = extend_dpg_methods(dpg)
dpg.create_context()
_,_, large_font = dpg.initialize_chinese_fonts(20,20,40)
dpg.bind_custom_theming()
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=True) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

@toggle_checkbox_and_disable(
        # "test group", 
        "test button"
        )
def _cb_(_, app_data, __):
    print(app_data)
    # raise Exception("Test exception")
    # print(app_data)
with dpg.window():
    dpg.add_checkbox(callback=_cb_)
    with dpg.group(tag= "test group"):
        btn = dpg.add_button(label="Test", tag = "test button")

dpg.bind_item_font(btn, large_font)
dpg.show_style_editor()
# dpg.show_font_manager()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
