#%%
import dearpygui.dearpygui as dpg
from camguihelper.core import _log
mapdata = (
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,1,8,9,1,1,1,
    0,0,0,2,14,38,53,14,6,0,
    0,0,1,8,40,137,111,49,7,0,
    0,0,0,10,51,116,108,38,8,0,
    0,0,0,2,18,44,48,20,4,1,
    0,0,0,1,6,11,5,6,0,0,
    0,0,0,0,1,0,1,0,0,0,
 )

dpg.create_context()
dpg.create_viewport(title='test', 
                    width=600, height=600, vsync=False
)
dpg.set_global_font_scale(1.3)
### initialzie two plots: master plot is on top of the slave plot. 
# the user interacts with the master plot, 
# which compels the slave plot to be in sync with its axes
pltkwargs = dict(
    pos = (10,20), 
    height= -1, width=-1, 
    query=False, 
    equal_aspects= True, no_frame=False,
    )
xyaxkwargs = dict(
    no_gridlines = True,
    no_tick_marks = True
    )
xkwargs = dict(label= "", 
               opposite=True
               )
ykwargs = dict(label= "", 
               invert=True
               )
xbeg, ybeg, xend, yend = 0,15, 10, 0
# xbeg, ybeg, xend, yend = 0,0, 10, 15
# xbeg, ybeg, xend, yend = 0,15, 10, 0
with dpg.value_registry():
    # dpg.add_float4_value(default_value = (-1,-1,1,1), tag='drfloat4')
    # dpg.add_float_vect_value(default_value = (-1,-1,1,1), tag='drfloat4')
    dpg.add_double4_value(default_value = (-1.,-1.,1.,1.), tag='drfloat4')
with dpg.window(width = 400, height= 500) as win1:
    with dpg.plot(tag="slave plot", **pltkwargs):
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis, tag= "slave xax", **xyaxkwargs, **xkwargs)
        with dpg.plot_axis(dpg.mvYAxis, tag = "slave yax", **xyaxkwargs, **ykwargs):
            hs = dpg.add_heat_series(mapdata,15,10,tag = "heat series",
                                scale_min=0, scale_max=137, 
                                bounds_min= (xbeg, ybeg), 
                                bounds_max= (xend, yend),
                                format=""
                                )
        dpg.fit_axis_data('slave xax')
        dpg.fit_axis_data('slave yax')
    with dpg.plot(tag="master plot", callback = _log, **pltkwargs):
        dpg.add_plot_axis(dpg.mvXAxis, tag= "master xax", **xyaxkwargs, **xkwargs)
        with dpg.plot_axis(dpg.mvYAxis, tag= "master yax", **xyaxkwargs, **ykwargs):
            scatterSeries = dpg.add_scatter_series(
                (xbeg,xbeg,xend,xend),
                (ybeg,yend,ybeg,yend),)
            with dpg.theme() as scatterThm:
                with dpg.theme_component(dpg.mvScatterSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (0,0,0,255), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, (0,0,0,0), category=dpg.mvThemeCat_Plots)
            dpg.bind_item_theme(scatterSeries, scatterThm)
        dr1 = dpg.add_drag_rect(
            default_value = (-1.,-1.,1.,1.), 
                                source='drfloat4', 
                                callback = lambda: print(dpg.get_value('drfloat4')))
with dpg.window(label = 'win2', width = 400, height= 500) as win2:
    with dpg.plot(tag="slave plot2", **pltkwargs):
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis, tag= "slave xax2", **xyaxkwargs, **xkwargs)
        with dpg.plot_axis(dpg.mvYAxis, tag = "slave yax2", **xyaxkwargs, **ykwargs):
            # dpg.add_heat_series(mapdata,15,10,tag = "heat series2",
            #                     scale_min=0, scale_max=137, 
            #                     bounds_min= (xbeg, ybeg), 
            #                     bounds_max= (xend, yend),
            #                     # format=""
            #                     )
            dpg.add_heat_series([],15,10,tag = "heat series2",
                                source= hs ,
                                scale_min=0, scale_max=137, 
                                bounds_min= (xbeg, ybeg), 
                                bounds_max= (xend, yend),
                                format=""
                                )
        # dpg.add_drag_rect(default_value = (-1,-1,1,1), source='drfloat4', callback = lambda: print(dpg.get_value('drfloat4')))
        # dpg.fit_axis_data('slave xax')
        # dpg.fit_axis_data('slave yax')
# print(dpg.get_value(scatterSeries))
print(dpg.get_value(hs))
with dpg.theme() as masterplot_theme:
    with dpg.theme_component(dpg.mvPlot):
        dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (0,0,0,0), category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_FrameBg, (0,0,0,0), category=dpg.mvThemeCat_Plots)
dpg.bind_item_theme("master plot", masterplot_theme)

### use a item_visible_handler to sync the slave axes to those of the master at every frame
# a seemingly more natural way is to use the `link_all_x` and `link_all_y` kwargs of the subplots.
# but I found it counterproductive having to worry about the subplots' layout behavior.
def sync_axes(_,__, user_data):
    """
    obtain master plot's axes range, using which we set the axes range of slave plot
    """
    xax_master, yax_master, xax_slave, yax_slave = user_data
    params_master = xmin_mst, xmax_mst, ymin_mst, ymax_mst = *dpg.get_axis_limits(xax_master), *dpg.get_axis_limits(yax_master)
    params_slave = *dpg.get_axis_limits(xax_slave), *dpg.get_axis_limits(yax_slave)
    if not params_master==params_slave:
        dpg.set_axis_limits(xax_slave, xmin_mst, xmax_mst)
        dpg.set_axis_limits(yax_slave, ymin_mst, ymax_mst)

with dpg.item_handler_registry() as ihrRect:
    def _cb(*args):
        if dpg.is_key_down(dpg.mvKey_LAlt):
            print('hello')
    # dpg.add_item_resize_handler(callback = _cb)
    dpg.add_item_deactivated_handler(callback = _cb)

def report_pos(sender, *args):
    print(dpg.get_value(sender))

dpg.add_button(parent=win1, label='hello', 
            #    callback=lambda: print(dpg.get_value('stuff'))
            #    callback=lambda: dpg.set_value(scatterSeries, [[-5,-5,5,5],[0,-10,0,-10], [], [], []])
               callback=lambda: print(dpg.get_value('stuff'))
               )

with dpg.item_handler_registry(tag= "master-slave sync hreg"):
    dpg.add_item_visible_handler(callback = sync_axes, user_data = ("master xax", "master yax", "slave xax", "slave yax"))
    def ctrl_add_rect(*args):
        if dpg.is_key_down(dpg.mvKey_LControl):
            x,y = dpg.get_plot_mouse_pos()
            dpg.add_drag_rect(parent = 'master plot', tag='stuff', callback= report_pos,
                                default_value=(x-0.5,y-0.5, x+0.5, y+0.5), color=(255,0,0)
                                )
            print(dpg.get_value(dpg.last_item()))
            # dpg.bind_item_handler_registry('stuff', ihrRect)
    dpg.add_item_clicked_handler(callback = ctrl_add_rect)
    dpg.add_item_clicked_handler(callback = lambda: print('hello'))
dpg.bind_item_handler_registry("master plot", "master-slave sync hreg")


dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
