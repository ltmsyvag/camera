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


with dpg.window(label = 'win1', width = 500, height = 500, pos= (0,0)) as win1:
    btnRd = dpg.add_button(label = 'redraw')
    ncols, ncells = 2,4
    with dpg.table(tag = 'the table'):
        for _ in range(ncols):
            dpg.add_table_column()
        for i in range(ncells):
            if i % ncols == 0:
                thisRow = dpg.add_table_row()
            with dpg.table_cell(parent = thisRow):
                dpg.add_button(label = 'button', tag = f'btn-{i}')
                dpg.set_item_callback(dpg.last_item(), lambda sender: print(sender))


def redraw(*args):
    dpg.delete_item('the table', children_only=True)
    for _ in range(ncols):
        dpg.add_table_column(parent = 'the table')
    ncells = 30
    for i in range(ncells):
        if i % ncols == 0:
            thisRow = dpg.add_table_row(parent = 'the table')
        with dpg.table_cell(parent = thisRow):
            dpg.add_button(label = 'button', tag = f'btn-{i}')
            dpg.set_item_callback(dpg.last_item(), lambda sender: print(sender))
dpg.set_item_callback(btnRd, redraw)

dpg.show_debug()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()