#%%
from camgui.helper import _log, _myRandFrame
import dearpygui.dearpygui as dpg
mapdata = _myRandFrame()
mapdata = (0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,0,0,0,0,0,0,
 0,0,0,0,1,8,9,1,1,1,
 0,0,0,2,14,38,53,14,6,0,
 0,0,1,8,40,137,111,49,7,0,
 0,0,0,10,51,116,108,38,8,0,
 0,0,0,2,18,44,48,20,4,1,
 0,0,0,1,6,11,5,6,0,0,
 0,0,0,0,1,0,1,0,0,0)

dpg.create_context()
dpg.create_viewport(title='test', 
                    width=600, height=600, vsync=False
)
dpg.set_global_font_scale(1.3)
### initialzie two plots: master plot is on top of the slave plot. 
# one interacts with the master plot, 
# which compels the slave plot to be in sync with its axes
_pltkwargs = dict(pos = (10,20), height= 400, width=400, query=False)
with dpg.window() as win1:
    with dpg.plot(tag="slave plot", no_frame=True, **_pltkwargs):
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis, tag= "slave xax")
        with dpg.plot_axis(dpg.mvYAxis, tag = "slave yax"):
            dpg.add_heat_series(mapdata,10,10,tag = "heat series",
                                scale_min=0, scale_max=137,
                                format="")
    with dpg.plot(tag="master plot", **_pltkwargs):
        dpg.add_plot_axis(dpg.mvXAxis, tag= "master xax")
        dpg.add_plot_axis(dpg.mvYAxis, tag= "master yax")
        dpg.add_drag_rect(tag = "drag rect", color = (255,0,0),
                          default_value=(-0.2,-0.2,0.2,0.2),)

### initialized the range of the master plot. 
# Or else the drag_rect takes up the whole plot upon gui launch
dpg.set_axis_limits("master xax", -0.5,1)
dpg.set_axis_limits("master yax", -0.5,1)
def _loosen_axes_lims():
    dpg.set_axis_limits_auto("master xax")
    dpg.set_axis_limits_auto("master yax")
dpg.set_frame_callback(1, _loosen_axes_lims) # need this, or else the resulting plot has fixed lims without any interactivity

### make the master plot transparent.
# by default its alpha == -255. 
# Not sure what a negative alpha means, 
# but it's not transparent by default
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
with dpg.item_handler_registry(tag= "master-slave sync hreg"):
    dpg.add_item_visible_handler(callback = sync_axes, user_data = ("master xax", "master yax", "slave xax", "slave yax"))
dpg.bind_item_handler_registry("master plot", "master-slave sync hreg")

dpg.setup_dearpygui()
dpg.show_viewport()
# dpg.show_style_editor()
dpg.start_dearpygui()
dpg.destroy_context()