#%%
import dearpygui.dearpygui as dpg
# import dearpygui.demo as demo
from camguihelper.dpghelper import *
# import time
import threading
dpg.create_context()
do_bind_my_default_global_theme()
do_initialize_chinese_fonts(20)
# winCritical = dpg.generate_uuid()
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571
import time
# with dpg.item_handler_registry() as ihr:
#     def _cb(_, app_data):
#         if dpg.get_active_window() != winCritical: # this check is essential !!
#             dpg.focus_item(winCritical)
#             # print(app_data)
#     dpg.add_item_visible_handler(callback= _cb)
def focus_critical_window(winCritical: int):
    while True:
        time.sleep(0.5) # lazy polling, save cpu cycles
        if not mouse_down_flag.is_set():
            if dpg.does_item_exist(winCritical):
                if dpg.get_active_window()!=winCritical:
                    dpg.focus_item(winCritical)
            else:
                break


def make_cricital_win(*args):
    with dpg.window(
                    width = 300, height = 300, pos= (0,0),
                    on_close= lambda sender: dpg.delete_item(sender)
                    ) as winCritical:
        dpg.add_button(label = 'kill myself', callback = lambda: dpg.delete_item(winCritical))
    dpg.configure_item(winCritical, label = winCritical)
    t_focus_winCritical = threading.Thread(target = focus_critical_window, args = (winCritical, ))
    t_focus_winCritical.start()

with dpg.window(label = 'win2', 
                on_close=lambda sender: dpg.delete_item(sender),
                # no_bring_to_front_on_focus=True
                ) as win2:
    # btn = dpg.add_button(label='kill win2', callback = lambda: dpg.delete_item(winCritical))
    btn2 = dpg.add_button(label = 'create win2', callback = make_cricital_win)
    btn3 = dpg.add_button(label = 'active wins', callback = lambda: print(dpg.get_active_window()))
    btn4 = dpg.add_button(label = 'make random win', callback = lambda: dpg.add_window())

with dpg.handler_registry():
    mouse_down_flag = threading.Event()
    dpg.add_mouse_click_handler(callback=lambda: mouse_down_flag.set())
    dpg.add_mouse_release_handler(callback=lambda: mouse_down_flag.clear())

# print(dpg.get_item_type(91))
dpg.setup_dearpygui()
dpg.show_viewport()

dpg.start_dearpygui()
dpg.destroy_context()


print('done')
# %%
