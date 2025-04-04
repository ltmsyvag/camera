#%%
import dearpygui.dearpygui as dpg
from math import sin, cos
from camgui.helper import _setChineseFont
sindatax = []
sindatay = []
cosdatay = []
for i in range(100):
    sindatax.append(i/100)
    sindatay.append(0.5 + 0.5*sin(50*i/100))
    cosdatay.append(0.5 + 0.75*cos(50*i/100))
dpg.create_context()
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

_setChineseFont(19)
with dpg.window() as win1:
    with dpg.subplots(1, 2, label="My Subplots", width=1200, height=-1,
                      link_all_x=True,link_all_y=True) as subplot_id:
            _width = -1
            with dpg.plot(no_title=True, pos= (0,0), width =_width):
                dpg.add_plot_axis(dpg.mvXAxis, label="", no_tick_labels=True)
                with dpg.plot_axis(dpg.mvYAxis, label="", no_tick_labels=True):
                    dpg.add_line_series(sindatax, sindatay, label="0.5 + 0.5 * sin(x)")
            with dpg.plot(no_title=True, pos= (0,0), width = _width):
                dpg.add_plot_axis(dpg.mvXAxis, label="", no_tick_labels=True)
                with dpg.plot_axis(dpg.mvYAxis, label="", no_tick_labels=True):
                    dpg.add_line_series(sindatax, cosdatay, label="0.5 + 0.5 * sin(x)")
# dpg.set_primary_window(win1, True)
dpg.show_style_editor()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()