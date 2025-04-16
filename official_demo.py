#%%
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from camguihelper.dpghelper import *

dpg.create_context()
initialize_chinese_fonts(20)

dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

demo.show_demo()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
