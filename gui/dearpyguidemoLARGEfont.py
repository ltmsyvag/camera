#%%
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo

dpg.create_context()
#### 下面的部分让 gui 字体大一些
# Load a custom font with a larger size
with dpg.font_registry():
    custom_font = dpg.add_font("/System/Library/Fonts/STHeiti Light.ttc", 22)  # macOS
    # custom_font = dpg.add_font("C:/Windows/Fonts/msyh.ttc", 20)  # Windows
    # Linux: "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# Bind the custom font globally
dpg.bind_font(custom_font)

dpg.create_viewport(title='Custom Title', width=600, height=600)

demo.show_demo()

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
