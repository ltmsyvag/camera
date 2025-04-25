#%%
import dearpygui.dearpygui as dpg
from mydpghelper import extend_dpg_methods
dpg = extend_dpg_methods(dpg)

dpg.create_context()
dpg.initialize_chinese_fonts(25)

dpg.create_viewport(title='DPG doc', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

dpg.show_documentation()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
