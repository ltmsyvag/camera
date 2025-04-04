#%%
import dearpygui.dearpygui as dpg

start_pos = [0, 0]
end_pos = [0, 0]
drawing_box = False
dpg.create_context()
def start_selection(sender, app_data):
    global start_pos, drawing_box
    start_pos = list(dpg.get_plot_mouse_pos())
    drawing_box = True

def update_selection(sender, app_data):
    global end_pos, drawing_box
    if drawing_box:
        end_pos = list(dpg.get_plot_mouse_pos())
        dpg.configure_item("selection_box", 
                           pmin=(start_pos[0], start_pos[1]),
                           pmax=(end_pos[0], end_pos[1]),
                           show=True)

def end_selection(sender, app_data):
    global drawing_box
    drawing_box = False
    print(f"Selection complete: {start_pos} to {end_pos}")

with dpg.window(label="Persistent Box Selection", width=600, height=500):
    with dpg.plot(label="Plot", width=-1, height=-1):
        dpg.add_plot_axis(dpg.mvXAxis, label="x", tag="x_axis")
        dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis")
        dpg.set_axis_limits("x_axis", 0, 10)
        dpg.set_axis_limits("y_axis", 0, 10)

        # Persistent rectangle for box selection
        dpg.draw_rectangle(pmin=(0, 0), 
                           pmax=(0, 0),
                           color=(255, 0, 0, 150),
                           thickness=2,
                           fill=(255, 0, 0, 50),  # Optional for transparent fill
                           tag="selection_box",
                           show=False)  # Start hidden

        # Handlers for mouse events
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(button=dpg.mvMouseButton_Left, callback=start_selection)
            dpg.add_mouse_drag_handler(button=dpg.mvMouseButton_Left, callback=update_selection)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=end_selection)


dpg.create_viewport(title="Persistent Box Selection", width=600, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()