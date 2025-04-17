#%%
import dearpygui.dearpygui as dpg

dpg.create_context()
dpg.create_viewport(title='Layout Demo', width=800, height=400)

with dpg.window(label="Main Window", width=800, height=400):

    total_width = 700
    left_width = int(total_width * 0.7)
    right_width = total_width - left_width

    with dpg.group(horizontal=True):
        with dpg.child_window(width=left_width, height=300, border=True):
            dpg.add_text("Left (70%)")
            with dpg.group():
                dpg.add_button(label="Button A")
                dpg.add_button(label="Button B")

        with dpg.child_window(width=right_width, height=300, border=True):
            dpg.add_text("Right (30%)")
            with dpg.group():
                dpg.add_input_text(label="Input")
                dpg.add_checkbox(label="Check")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()