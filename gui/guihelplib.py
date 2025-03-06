#%%
import platform
def chinesefontpath():
    system = platform.system()

    if system == "Windows": return r"C:/Windows/Fonts/msyh.ttc"
    elif system == "Darwin": return r"/System/Library/Fonts/STHeiti Light.ttc"
    else: raise NameError("没有定义本操作系统的中文字体地址")

if __name__ == "__main__":
    print(chinesefontpath())