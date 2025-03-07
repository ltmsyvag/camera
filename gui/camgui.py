#%%
import dearpygui.dearpygui as dpg
from guihelplib import setChineseFont, _log, chinesefontpath

dpg.create_context()
default_fontsize, large_fontsize = 19, 100
setChineseFont(dpg, fontsize=default_fontsize)
# default_font = dpg.font(chinesefontpath(), default_fontsize)
# large_font = dpg.font(chinesefontpath(), large_fontsize)

dpg.create_viewport(title='cam-AWG GUI', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571
with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll): # online doc: theme components must have a specified item type. This can either be `mvAll` for all items or a specific item type
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1, 
                            category=dpg.mvThemeCat_Core # online docstring paraphrase: you are mvThemeCat_core, if you are not doing plots or nodes. 实际上我发现不加这个 kwarg 也能产生出想要的 theme。但是看到网上都加，也就跟着加吧
                            )
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 10, category=dpg.mvThemeCat_Core)
dpg.bind_theme(global_theme)

with dpg.window(tag="win1", pos=(0,0)):
    camOFFlabel, camONlabel = "相机已关闭", "相机已开启"
    camSwitch = dpg.add_button(width=150, height=150, label=camOFFlabel)

# dpg.set_primary_window("win1", True)

## camSwitch: camera power switch button

mycol_redActive = 255,0,0
mycol_greenActive = 0,255,0
with dpg.theme() as camONbtn_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (25, 219, 72), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, mycol_greenActive, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, mycol_greenActive, category=dpg.mvThemeCat_Core) 
with dpg.theme() as camOFFbtn_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (202, 33, 33), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, mycol_redActive, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, mycol_redActive, category=dpg.mvThemeCat_Core)

def camSwitch_callback(sender, app_data, user_data):
  state, = user_data
  state = not state
  dpg.set_item_label(camSwitch, camONlabel if state else camOFFlabel)
  dpg.bind_item_theme(sender, camONbtn_theme if state is True else camOFFbtn_theme)
  dpg.set_item_user_data(sender, (state,))

dpg.set_item_callback(camSwitch, camSwitch_callback)
dpg.set_item_user_data(camSwitch, (False,))
dpg.bind_item_theme(camSwitch, camOFFbtn_theme)
# dpg.bind_item_font(camSwitch, large_font)

# dpg.show_style_editor()
# dpg.show_item_registry()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()