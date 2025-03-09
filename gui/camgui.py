#%%
import dearpygui.dearpygui as dpg
from guihelplib import (_log, _setChineseFont,rgbOppositeTo, guiOpenCam, guiSetExposure)

dpg.create_context()

_, large_font = _setChineseFont(dpg,
                                default_fontsize=19,
                                large_fontsize=30)

dpg.create_viewport(title='cam-AWG GUI', 
                    width=1000, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571
with dpg.theme(label="global theme") as global_theme:
    with dpg.theme_component(dpg.mvAll): # online doc: theme components must have a specified item type. This can either be `mvAll` for all items or a specific item type
        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1, 
                            category=dpg.mvThemeCat_Core # online docstring paraphrase: you are mvThemeCat_core, if you are not doing plots or nodes. 实际上我发现不加这个 kwarg 也能产生出想要的 theme。但是看到网上都加，也就跟着加吧
                            )
dpg.bind_theme(global_theme)

with dpg.window(tag="win1", pos=(0,0)):
    with dpg.child_window(width=300):
        camSwitch = dpg.add_button(
            width=150, height=70, user_data={
                "is on" : False, 
                "camera object" : None, 
                "camera off label" : "相机已关闭",
                "camera on label" : "相机已开启",
                "camera off rgb" : (202, 33, 33),
                "camera off hovered rgb" : (255, 0, 0),
                "camera on rgb" : (25,219,72),
                "camera on hovered rgb" : (0,255,0),
                })
        _1 = dpg.get_item_user_data(camSwitch)
        dpg.set_item_label(camSwitch, _1["camera off label"])
        dpg.add_separator()
        fieldExpo = dpg.add_input_float(
            width = 100, label="exposure time (ms)", step=0, callback=_log,
            max_value= 1800e3, max_clamped=True, # 最大曝光时间 1800 秒
            min_value= (7.2e-6)*1e3, min_clamped=True, # 最小曝光时间 7.2e-6 秒
            default_value= 100
            )
        def exposureFieldCallback(sender, app_data, user_data): # the app_data in this case is the same as dpg.get_value(fieldExpo)
            cam = dpg.get_item_user_data(camSwitch)["camera object"]
            if cam:
                guiSetExposure(cam, app_data)
        dpg.set_item_callback(fieldExpo, exposureFieldCallback)
        dpg.add_separator(label="ROI")
        with dpg.group(horizontal=False):
            dpg.add_text("h start & h length")
            dpg.add_input_floatx(size=2, callback=lambda : print("hello"))
            dpg.add_text("v start & v length")
            dpg.add_input_floatx(size=2)
dpg.set_primary_window("win1", True)

#==== camSwitch: camera power switch button
dpg.bind_item_font(camSwitch, large_font)

## 设置 cam switch 开关的 theme
_1 = dpg.get_item_user_data(camSwitch)["camera on rgb"]
_2 = dpg.get_item_user_data(camSwitch)["camera off rgb"]
_3 = dpg.get_item_user_data(camSwitch)["camera on hovered rgb"]
_4 = dpg.get_item_user_data(camSwitch)["camera off hovered rgb"]
with dpg.theme(label="cam switch ON") as camONbtn_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _1, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _3, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _3, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_1), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15, category=dpg.mvThemeCat_Core)
with dpg.theme(label="cam switch OFF") as camOFFbtn_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _2, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _4, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _4, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_2), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15, category=dpg.mvThemeCat_Core)

def camSwitch_callback(sender, app_data, user_data):
    state, cam, camONlabel, camOFFlabel = user_data["is on"], user_data["camera object"], user_data["camera on label"], user_data["camera off label"]
    state = not state # flip the state
    if state:
        dpg.set_item_label(camSwitch,"开启中...")
        cam = guiOpenCam()
        cam.set_exposure(dpg.get_value(fieldExpo)*1e-3)
        # print(cam.cav["exposure_time"])
        dpg.set_item_label(camSwitch, camONlabel)
        dpg.bind_item_theme(sender, camONbtn_theme)
    else:
        cam.close(); print("=====cam closed")
        cam = None
        dpg.set_item_label(camSwitch, camOFFlabel)
        dpg.bind_item_theme(sender, camOFFbtn_theme)
    user_data.update({"is on": state, "camera object": cam})
    dpg.set_item_user_data(sender, user_data)

dpg.set_item_callback(camSwitch,camSwitch_callback)
dpg.bind_item_theme(camSwitch, camOFFbtn_theme)

# print(dpg.get_value(fieldExpo))
# dpg.show_style_editor()
dpg.show_item_registry()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
