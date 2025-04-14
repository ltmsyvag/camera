#%%
import dearpygui.dearpygui as dpg
from mydpghelper import _setChineseFont, extend_dpg_methods
dpg = extend_dpg_methods(dpg)
import time


dpg.create_context()
_, bold_font, large_font = _setChineseFont(
                                default_fontsize=19,
                                bold_fontsize=21,
                                large_fontsize=30)
toggle_decor = dpg.initialize_toggle_btn()

dpg.create_viewport(title='Custom Title', width=600, height=600)

with dpg.window():
    dpg.add_button(label= "hello", width = 150, height = 70, 
                #    enabled=False,
                   user_data={
                        "is on" : False,
                        "on label" : "on",
                        "off label" : "off",
                        })
    _tag = dpg.last_item()
    cbox = dpg.add_checkbox()
dpg.bind_item_font(_tag, large_font)

@toggle_decor(cbox)
def _cb(*args,**kwargs):
    time.sleep(0.5)
    # raise Exception
dpg.set_item_callback(_tag, _cb)
print(
    type(dpg.get_item_type(_tag))
    )
dpg.show_style_editor()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
