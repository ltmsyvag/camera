#%%
import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.set_global_font_scale(1.5)

dpg.create_viewport(title='Custom Title', width=600, height=600)

with dpg.window():
    btn = dpg.add_button(label= "hello", width = 150, height = 70, enabled=False,)
    toggle = dpg.add_button(label= "toggle", width = 150, height = 70,)

with dpg.theme() as mytheme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (202,33,33), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255,0,0), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255,0,0), category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15, category=dpg.mvThemeCat_Core)

dpg.bind_item_theme(btn, mytheme)

def _cb(*args):
    state = dpg.get_item_configuration(btn)["enabled"]
    dpg.configure_item(btn, enabled=not state)
    
dpg.set_item_callback(toggle, _cb)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
