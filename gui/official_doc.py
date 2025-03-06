#%%
import dearpygui.dearpygui as dpg
from guihelplib import setChineseFont

dpg.create_context()
setChineseFont(dpg, fontsize=20)

dpg.create_viewport(title='DPG doc', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

dpg.show_documentation()
dpg.show_item_registry()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
