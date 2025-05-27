#%%
import dearpygui.dearpygui as dpg
# import dearpygui.demo as demo
from camguihelper.dpghelper import *
import time
dpg.create_context()
do_bind_my_default_global_theme()
do_initialize_chinese_fonts(20)
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571


with dpg.window(width = 500, height = 500, pos= (0,0)):
    with dpg.plot(width=-1, height=-1, equal_aspects=True, user_data={'dr being dragged':None}) as thePlot:
        dpg.add_plot_axis(dpg.mvXAxis, opposite=True)
        dpg.set_axis_limits(dpg.last_item(), 0, 10)
        dpg.add_plot_axis(dpg.mvYAxis, invert=True)
        dpg.set_axis_limits(dpg.last_item(), 0, 10)
        dr = dpg.add_drag_rect(default_value=(5, 5, 6, 6))
        def snap_rect(sender, *args):
            mdh_dict = dpg.get_item_user_data(thePlot)
            if mdh_dict['dr being dragged'] is None:
                mdh_dict['dr being dragged'] = sender
        dpg.set_item_callback(dpg.last_item(), snap_rect)

with dpg.item_handler_registry() as ihr:
    dpg.add_item_clicked_handler(callback= lambda: print('clicked'))
with dpg.handler_registry():
    def _cb(*args):
        thePlot_dict = dpg.get_item_user_data(thePlot)
        dr = thePlot_dict['dr being dragged']
        if dr is not None:
            x1, y1, x2, y2 = dpg.get_value(dr)
            dpg.set_value(dr, (round(x1), round(y1), round(x2), round(y2)))
            thePlot_dict['dr being dragged'] = None
        
    mrh = dpg.add_mouse_release_handler(callback= _cb)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
