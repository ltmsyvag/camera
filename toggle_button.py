#%%
import dearpygui.dearpygui as dpg
from helper import _setChineseFont
from helper import rgbOppositeTo

with dpg.theme(label="cam switch OFF") as theme_btnoff:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (255), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _4, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _4, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_2), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15, category=dpg.mvThemeCat_Core)

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
# %%
