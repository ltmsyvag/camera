#%%
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
from camguihelper.dpghelper import *

dpg.create_context()
# do_bind_my_global_theme()
do_initialize_chinese_fonts(20)
dpg.create_viewport(title='Custom Title', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

with dpg.window():
    hello = dpg.add_text('hello', tag='hello')
    dpg.add_button(label = 'hello tag', callback = lambda: print(hello))

with dpg.item_handler_registry() as ihr:
    dpg.add_item_double_clicked_handler(callback= lambda sender, app_data, user_data: print('sender', sender , 'app_data', app_data)) 

dpg.bind_item_handler_registry(hello, ihr)
# demo.show_demo()
# dpg.show_style_editor()

print(dpg.get_item_alias('hello'))
print(dpg.get_item_alias(hello))
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
