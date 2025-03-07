#%%
import platform
from types import ModuleType # 用于 type annotation
# import dearpygui.dearpygui as dpg

def chinesefontpath() -> str:
    """
    返回中文字体地址，以便 dpg 调用
    """
    system = platform.system()
    if system == "Windows": return r"C:/Windows/Fonts/msyh.ttc"
    # elif system == "Darwin": return r"/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    elif system == "Darwin": return r"/System/Library/Fonts/Monaco.ttf" # 没有中文字体, 但是读文档舒服
    # elif system == "Darwin": return r"/Users/haiteng/Library/Fonts/sarasa-term-sc-nerd.ttc"
    else: raise NameError("没有定义本操作系统的中文字体地址")

def setChineseFont(dpg: ModuleType, fontsize: int) -> None:
    """
    （必须放置在 `dpg.create_context()` 之后）为 dpg 设置支持中文的默认字体
    """
    with dpg.font_registry():
        with dpg.font(chinesefontpath(), fontsize) as default_font:
            ## 本函数的方案来自于 https://www.skfwe.cn/p/dearpygui-显示中文和特殊字符/
            ## 但是我发现实际上起作用的指令就一条，于是把其他指令注释掉了。其他指令可能有其他应用
            # dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
            # dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Simplified_Common) # 不包含锶铷这类生僻字
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)   # @source 这个会影响启动速度
            # dpg.add_font_range(0x300, 0x400)
        dpg.bind_font(default_font)


def _log(sender, app_data, user_data):
    """
    helper function from demo.py. 可以作为还没写好的 callback 的 placeholder，
    coding 时用来查看 callback 的所有三个 argument：
    - sender：the id of the UI item that submitted teh callback
    - app_data: occasionally UI items will send their own data (e.g. file dialog)
    - user_data: any python object you want to send to the function
    (quoted from dpg online doc)
    """
    print(f"sender: {sender}, \t app_data: {app_data}, \t user_data: {user_data}")


if __name__ == "__main__":
    print(chinesefontpath())