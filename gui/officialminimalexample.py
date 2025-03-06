#%%
import dearpygui.dearpygui as dpg
from guihelplib import chinesefontpath


def save_callback():
    print("Save Clicked")

dpg.create_context()
with dpg.font_registry():
    custom_font = dpg.add_font(chinesefontpath(), 21)  # macOS
    # custom_font = dpg.add_font("C:/Windows/Fonts/msyh.ttc", 20)  # Windows
    # Linux: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# Bind the custom font globally
dpg.bind_font(custom_font)
dpg.create_viewport()
dpg.setup_dearpygui()

with dpg.window(label="Example Window"):
    dpg.add_text("Hello world")
    dpg.add_button(label="Save", callback=save_callback)
    dpg.add_input_text(label="string")
    dpg.add_slider_float(label="float")

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()