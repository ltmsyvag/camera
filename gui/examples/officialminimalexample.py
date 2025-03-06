#%%
import dearpygui.dearpygui as dpg
from guihelplib import setChineseFont
## 根据 https://dearpygui.readthedocs.io/en/latest/tutorials/first-steps.html。 gui 创建有 6 个 MUST steps， 写在下面的注释中

def save_callback():
    print("Save Clicked")

dpg.create_context() # MUST: create the context
setChineseFont(dpg, 20)

dpg.create_viewport() # MUST" create the viewport
dpg.setup_dearpygui() # MUST: setup dearpygui

with dpg.window(label="Example Window"):
    dpg.add_text("Hello world")
    dpg.add_button(label="Save", callback=save_callback)
    dpg.add_input_text(label="string")
    dpg.add_slider_float(label="float")

dpg.show_viewport()  # MUST: show the viewport
dpg.start_dearpygui() # MUST: start dearpygui
dpg.destroy_context() # MUST: clean up the context
# %%
