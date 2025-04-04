#%%
import dearpygui.dearpygui as dpg
from helper import _setChineseFont

dpg.create_context()
dpg.create_viewport(title='Custom Title', width=600, height=600)
_, bold_font, large_font = _setChineseFont(
                                default_fontsize=19,
                                bold_fontsize=21,
                                large_fontsize=30)
with dpg.window():
    dpg.add_button(label= "hello", width = 150, height = 70,
                   user_data={
                        "is on" : False, 
                        "camera object" : None, 
                        "camera off label" : "cam closed",
                        "camera on label" : "cam opened",
                        "camera off rgb" : (202, 33, 33),
                        "camera off hovered rgb" : (255, 0, 0),
                        "camera on rgb" : (25,219,72),
                        "camera on hovered rgb" : (0,255,0),
                        })
    _tag = dpg.last_item()
    _dict = dpg.get_item_user_data(_tag)
    dpg.set_item_label(_tag, _dict["camera off label"])
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()