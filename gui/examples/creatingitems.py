#%% https://dearpygui.readthedocs.io/en/latest/tutorials/item-usage.html
import dearpygui.dearpygui as dpg

dpg.create_context()

with dpg.window(tag="the window", label="Tutorial"):
    b0 = dpg.add_button(label="button 0")
    b1 = dpg.add_button(tag=100, label="Button 1")
    b3=dpg.add_button(tag="Btn2", label="Button 2")

print(dpg.get_item_label("the window"))
print(b0)
print(b1)
print(dpg.get_item_label("Btn2"))
print(b3)

dpg.create_viewport(title='Custom Title', width=600, height=200)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()