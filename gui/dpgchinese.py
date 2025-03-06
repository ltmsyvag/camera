# -*- coding: utf-8 -*-
#********************************************************************************
#Copyright © 2023 Wcq
#File Name: test_unicode.py
#Author: Wcq
#Email: wcq-062821@163.com
#Created: 2023-11-29 10:26:56 
#Last Update: 2023-11-29 10:37:40
#         By: Wcq
#Description: 
#********************************************************************************
#%%
import dearpygui.dearpygui as dpg

dpg.create_context()
print(f"Ω Unicode : 0x{ord('Ω'):04x}")
print(f"ant Unicode : 0x{ord('🐜'):06x}")
with dpg.font_registry():
    with dpg.font("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 20) as default_font:
        # add the default font range
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common)
        # dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)   # 这个会影响启动速度
        dpg.add_font_range(0x300, 0x400)
        dpg.bind_font(default_font)

dpg.create_viewport(title='Custom Title', width=800, height=600)
with dpg.window(label='测试中文 Ω', width=800, height=300):
    dpg.add_text(label='test' , default_value='测试 θ \u03a9')
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
