#%%
import dearpygui.dearpygui as dpg
# import dearpygui.demo as demo
from camguihelper.dpghelper import *
# import time
dpg.create_context()
do_bind_my_default_global_theme()
do_initialize_chinese_fonts(20)
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

with dpg.item_handler_registry() as ihr:
    def _cb(_, app_data):
        if dpg.get_active_window() != win2: # this check is essential !!
            dpg.focus_item(win2)
            print(app_data)
    dpg.add_item_visible_handler(callback= _cb)

with dpg.window(label = 'win1', width = 500, height = 500, pos= (0,0)) as win1:
    ...
with dpg.window(label = 'win2', 
                on_close=lambda sender: dpg.delete_item(sender),
                # no_bring_to_front_on_focus=True
                ) as win2:
    btn = dpg.add_button(label='close win2', callback = lambda: dpg.delete_item(win2))
    btn2 = dpg.add_button(label = 'active wins', callback = lambda: print(dpg.get_active_window()))

def _cb(*args):
    # dpg.delete_item(ihr)
    # dpg.configure_item(win2, focus = False)
    # print(dpg.get_item_configuration(win2))
    # dpg.delete_item(ihr)
    dpg.delete_item(win2)
dpg.set_item_callback(btn, _cb)
dpg.bind_item_handler_registry(win2, ihr)

# print(dpg.get_item_type(91))
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
