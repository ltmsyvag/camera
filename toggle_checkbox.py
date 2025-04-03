#%%
import dearpygui.dearpygui as dpg
from camgui.helper import _setChineseFont, _log
import spcm


dpg.create_context()
dpg.create_viewport(title='Custom Title', width=600, height=600)
with dpg.theme(label="global theme") as global_theme:
    with dpg.theme_component(dpg.mvAll): # online doc: theme components must have a specified item type. This can either be `mvAll` for all items or a specific item type
        # dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1, 
        #                     category=dpg.mvThemeCat_Core # online docstring paraphrase: you are mvThemeCat_core, if you are not doing plots or nodes. 实际上我发现不加这个 kwarg 也能产生出想要的 theme。但是看到网上都加，也就跟着加吧
        #                     )
        dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (255,255,0), category=dpg.mvThemeCat_Core)
dpg.bind_theme(global_theme)
_, bold_font, large_font = _setChineseFont(
                                default_fontsize=19,
                                bold_fontsize=21,
                                large_fontsize=30)
with dpg.window():
    def _cb(sender, app_data, user_data):
        if app_data:
            raw_card = spcm.Card(card_type=spcm.SPCM_TYPE_AO)
            raw_card.open('/dev/spcm0')
            card_handle = raw_card.handle()
            dpg.set_item_user_data(sender, card_handle)
            print("opened")
        else:
            card_handle = user_data
            raw_card.close(card_handle)
            print("closed")
    dpg.add_checkbox(label="AWG open/close",callback=_cb)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()