#%%
import dearpygui.dearpygui as dpg
from guihelplib import _setChineseFont
import numpy as np

np.random.seed(42)
# Sample data for heatmap
data = np.random.rand(10, 10)

# Initial rectangle position and size
rect_pos = [2, 2]
rect_size = [3, 3]

dpg.create_context()
_setChineseFont(19)
def on_drag(sender, app_data):
    rect_pos[0] = app_data[0]
    rect_pos[1] = app_data[1]
    rect_size[0] = app_data[2] - app_data[0]
    rect_size[1] = app_data[3] - app_data[1]
    print(f"New Rect: {rect_pos}, Size: {rect_size}")

with dpg.window(label="Heatmap with Draggable Rect", width=600, height=500):

    # **Bottom plot** for heatmap
        # dpg.set_axis_limits("x_axis", 0, 10)
        # dpg.set_axis_limits("y_axis", 0, 10)

    with dpg.plot(label="Heatmap", width=-1, height=-1, tag="bottom_plot"):
        dpg.add_plot_axis(dpg.mvXAxis, label="X", tag="x_axis")
        dpg.add_plot_axis(dpg.mvYAxis, label="Y", tag="y_axis")
        dpg.add_heat_series(data.flatten(), 10, 10, parent="y_axis", bounds_min=(-5, -5), bounds_max=(0, 0))
    # with dpg.plot(label="Heatmap", width=-1, height=-1, tag="bottom_plot2"):
    #     dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
    #     dpg.add_plot_axis(dpg.mvXAxis, label="X", tag="x_axis2")
    #     dpg.add_plot_axis(dpg.mvYAxis, label="Y", tag="y_axis2")
    #     dpg.add_heat_series(data.flatten(), 5, 5, parent="y_axis2", bounds_min=(0, 0), bounds_max=(5, 5))
    if False:
        # **Top transparent plot** for drag rect
        with dpg.plot(label="", width=-1, height=-1, tag="top_plot", 
                    #   no_title=True, no_menus=True, no_box_select=True
                      ):
            dpg.add_plot_axis(dpg.mvXAxis, label="", tag="top_x_axis", no_tick_marks=True, no_tick_labels=True)
            dpg.add_plot_axis(dpg.mvYAxis, label="", tag="top_y_axis", no_tick_marks=True, no_tick_labels=True)

            # Sync limits with the heatmap plot
            # dpg.set_axis_limits("top_x_axis", 0, 10)
            # dpg.set_axis_limits("top_y_axis", 0, 10)

            # Transparent background (so it doesn't cover the heatmap)
            # dpg.bind_item_theme("top_plot", None)
            dpg.add_heat_series(data.flatten(), 10, 10, parent="top_y_axis", bounds_min=(0,0), bounds_max=(5, 5))
            # dpg.add_drag_rect(
            #     color = [255,0,0,255], default_value=(-5,-5,0,0),
            #     )
            # Create draggable rectangle on top plot
            # dpg.add_drag_rect(
            #     pmin=(rect_pos[0], rect_pos[1]),
            #     pmax=(rect_pos[0] + rect_size[0], rect_pos[1] + rect_size[1]),
            #     color=(255, 0, 0, 150),  # Red with transparency
            #     thickness=2,
            #     callback=on_drag,
            #     tag="selection_rect"
            # )

dpg.show_style_editor()
dpg.create_viewport(title="Heatmap Example", width=600, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()