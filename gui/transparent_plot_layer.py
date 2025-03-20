#%%
from guihelplib import _log, _myRandFrame
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

def _pval(sender):
    print(dpg.get_value(sender))
dpg.create_context()
dpg.create_viewport(title='test', 
                    width=600, height=600, vsync=False
)
dpg.set_global_font_scale(1.3)

with dpg.window() as win1:
    with dpg.plot(tag="the plot", label="Heat Series", no_mouse_pos=True, height=400, width=400,
                #   query=True, 
                #   min_query_rects=0,
                #   max_query_rects=0,
                  callback=_log):
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis, tag= "xax")
        with dpg.plot_axis(dpg.mvYAxis, tag = "yax"):
            dpg.add_heat_series(mapdata,
                                10,10,
                                tag = "heat series",
                                scale_min=0, 
                                scale_max=137,
                                format=""
                                )
    with dpg.plot(tag="the plot2", pos= (10,10),label="Heat Series 2", no_mouse_pos=True, height=400, width=400,
                  query=True, 
                  no_frame = True,
                #   max_query_rects=0,
                  callback=_log):
        # dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis, tag= "xax2")
        with dpg.plot_axis(dpg.mvYAxis, tag = "yax2"):
            dpg.add_heat_series(mapdata,
                                10,10,
                                tag = "heat series2",
                                scale_min=0, 
                                scale_max=137,
                                format=""
                                )
        dpg.add_drag_rect(color = (255,0,0), default_value=(-0.5,-0.5,0.2,0.2),)
print(dpg.get_item_pos("the plot"))
with dpg.theme() as foreplot_theme:
    with dpg.theme_component(dpg.mvPlot):
        dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (0,0,0,0), category=dpg.mvThemeCat_Plots)
        # dpg.add_theme_color(dpg.mvPlotCol_FrameBg, (0,0,0,0), category=dpg.mvThemeCat_Plots)
        # dpg.add_theme_style(dpg.mvPlotCol_PlotBg, (255,0,0,0), category=dpg.mvThemeCat_Core)

dpg.bind_item_theme("the plot2", foreplot_theme)

# dpg.show_documentation()
# dpg.show_debug()
# dpg.show_item_registry()
dpg.show_style_editor()
# dpg.set_primary_window(win1, True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()