#%%
import dearpygui.dearpygui as dpg

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

with dpg.window() as win1:
    with dpg.plot(label="Heat Series", no_mouse_pos=True, height=-1, width=-1):
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis)
        with dpg.plot_axis(dpg.mvYAxis):
            dpg.add_heat_series(mapdata,
                                10,10,
                                scale_min=0, 
                                scale_max=137,
                                format=""
                                )
        dpg.add_drag_rect(color = [255,0,0,255], default_value=(-0.5,-0.5,0.2,0.2),)

dpg.set_primary_window(win1, True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()