#%%
import dearpygui.dearpygui as dpg
# import dearpygui.demo as demo
from camguihelper.dpghelper import *
# import time
dpg.create_context()
do_bind_my_default_global_theme()
do_initialize_chinese_fonts(20)
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

winId = dpg.generate_uuid()
with dpg.window(tag = winId, label = 'win1', width = 500, height = 500, pos= (0,0)):
    ...
print('original winId', winId)
def _frame_cb():
    dpg.set_item_alias(winId, 'my window')
    dpg.add_alias('my window', winId)
    print('winId', winId)
    print('my window', dpg.get_alias_id('my window'))
dpg.set_frame_callback(1, _frame_cb)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
