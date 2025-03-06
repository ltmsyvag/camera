#%%
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from guihelplib import setChineseFont

dpg.create_context()
setChineseFont(dpg, fontsize=20)

dpg.create_viewport(title='Custom Title', width=600, height=600)

demo.show_demo()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
