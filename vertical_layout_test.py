#%%
import dearpygui.dearpygui as dpg

dpg.create_context()
# Force layout size management
def resize_callback(*args):
    # Get total window size
    width, height = dpg.get_item_rect_size(main_window_id)

    # Reserve space: 40px top controls, 40px bottom controls, margin
    reserved_height = 40 + 40 + 10
    dpg.configure_item(resizable_child_id, height=height - reserved_height)

with dpg.item_handler_registry() as ihr:
    dpg.add_item_resize_handler(callback=resize_callback
                                )
with dpg.window(label="Main Window", width=600, height=500,
                # resize_callback = lambda:print('hello')
                ) as main_window_id:

    # Top controls
    with dpg.group(horizontal=True):
        dpg.add_button(label="Top Button 1")
        dpg.add_button(label="Top Button 2")

    # Resizable middle region
    resizable_child_id = dpg.generate_uuid()
    with dpg.child_window(tag=resizable_child_id):
        dpg.add_text("Resizable Plot Area")
        dpg.add_colormap_scale()  # Or dpg.add_plot(), etc.

    # Bottom controls
    with dpg.group(horizontal=True):
        dpg.add_button(label="Bottom Button 1")
        dpg.add_button(label="Bottom Button 2")

dpg.bind_item_handler_registry(main_window_id, ihr)

# dpg.set_item_callback(main_window_id)
# dpg.set_viewport_resize_callback(resize_callback)

dpg.create_viewport(title='Resizable Plot Fix', width=600, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()
# resize_callback(None, None)  # Initialize layout
dpg.start_dearpygui()
dpg.destroy_context()