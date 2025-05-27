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
            x1r, y1r, x2r, y2r = round(x1), round(y1), round(x2), round(y2)
            if len(set([x1r, y1r, x2r, y2r])) < 4:
                if abs(y1 - y2) < 0.5:
                    if int(y2) == y2:
                        y1r = y2+1 if y1>y2 else y2-1
                    else:
                        y2r = y1+1 if y1<y2 else y1-1
                if abs(x1 - x2) < 0.5:
                    if int(x2) == x2:
                        x1r = x2+1 if x1>x2 else x2-1
                    else:
                        x2r = x1+1 if x1<x2 else x1-1
            dpg.set_value(dr, (x1r, y1r, x2r, y2r))
            thePlot_dict['dr being dragged'] = None
        
    mrh = dpg.add_mouse_release_handler(callback= _cb)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
