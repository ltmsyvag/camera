#%%
import dearpygui.dearpygui as dpg
from helper import _setChineseFont
from helper import rgbOppositeTo
import time

#%% def themes for toggle button
dpg.create_context()
_, bold_font, large_font = _setChineseFont(
                                default_fontsize=19,
                                bold_fontsize=21,
                                large_fontsize=30)

_off_rgb = (202, 33, 33) # off rgb 
_offhov_rgb = (255, 0, 0) # off hovered rgb
_on_rgb = (25,219,72) # on rgb 
_onhov_rgb = (0,255,0) # on hovered rgb 
_1 = 15 # frame rounding
with dpg.theme() as theme_btnoff:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _off_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _offhov_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _offhov_rgb, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_off_rgb), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)
with dpg.theme() as theme_btnon:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _on_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _onhov_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _onhov_rgb, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_on_rgb), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, _1, category=dpg.mvThemeCat_Core)

def prep_toggle_button(func):
    assert func == dpg.add_button, "decoratee must be dpg.add_button"
    def wrapper(*args, **kwargs):
        btn = func(*args, **kwargs)
        if "user_data" in kwargs:
            if isinstance(kwargs["user_data"], dict):
                _dict = kwargs["user_data"]
                if "is on" in _dict:
                    if _dict["is on"]:
                        dpg.bind_item_theme(btn, theme_btnon)
                        if "on label" in _dict:
                            dpg.set_item_label(btn, _dict["on label"])
                    else:
                        dpg.bind_item_theme(btn, theme_btnoff)
                        if "off label" in _dict:
                            dpg.set_item_label(btn, _dict["off label"])
        return btn
    return wrapper

def toggle_btn_state(cb):
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
        except:
            dpg.set_item_label(sender, "错误!")
            return # exit early 

        if state:
            dpg.bind_item_theme(sender, theme_btnon)
            if "on label" in user_data:
                dpg.set_item_label(sender, user_data["on label"])
        else:
            dpg.bind_item_theme(sender, theme_btnoff)
            if "off label" in user_data:
                dpg.set_item_label(sender, user_data["off label"])
        user_data["is on"] = state
        dpg.set_item_user_data(sender, user_data) # store state
    return wrapper

dpg.add_button = prep_toggle_button(dpg.add_button)

dpg.create_viewport(title='Custom Title', width=600, height=600)

with dpg.window():
    dpg.add_button(label= "hello", width = 150, height = 70,
                   user_data={
                        "is on" : False,
                        "on label" : "on",
                        "off label" : "off",
                        })
_tag = dpg.last_item()
dpg.set_item_font(_tag, large_font)

@toggle_btn_state
def _cb(*args,**kwargs):
    time.sleep(0.5)
    raise Exception
dpg.set_item_callback(_tag, _cb)
print(
    type(dpg.get_item_type(_tag))
    )
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
