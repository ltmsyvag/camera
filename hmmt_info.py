#%% 把 dir(cam) 能干的事情全部试一次
import pylablib as pll
from pylablib.devices import DCAM # gives error if dll is not found. The dll is by default in system32 folder and automatically found. if not, then use code `pll.par["devices/dlls/dcamapi"] = "path/to/dlls"`
with DCAM.DCAMCamera() as cam:
    # cam.set_roi(0,128,0,128)
    # images = cam.grab(10)

    print(cam.acquisition_in_progress()) # 返回 True/False. docstring: Check if acquisition is in progress
    # cam.apply_settings() # takes a key-val setting dict
    assert cam.attributes == cam.get_all_attributes() # 这两个字典是完全相同的，seems not pythonic, might prefer the shorter code
    for key, val in list(cam.attributes.items())[:5]: # preview 前 3 个特性。min/max 等有用数值给出，但是 value 不给出
        print(key, "||",val)
    print(cam.ca["exposure_time"]) # 等价于 cam.get_attribute("exposure_time")。给出一个 DCAMAttribute （e.g. exposure_time）, 适用于看 min/max，但是不能看值（用 cav 看）
    attr = cam.ca["exposure_time"] # 上面的 attribute 可以直接作为对象
    print( # 给出一些有用的对象的属性。attr.update_limits() 有时也是有用的，见 pylablib docstring。
        attr.get_value(), # 也可以用后面的 cav 方法获得
        attr.min, 
        attr.max,
        attr.readable,
        attr.writable,
        attr.step, # 值可变的最小单位
        attr.unit, # not sure what this is 
        attr.values, # not sure what it does, 返回列表
        ) 
    print(cam.cav["exposure_time"]) # 等价于 cam.get_attribute_value("exposure_time")。给出一个 DCAMAttribute（e.g. exposure_time）的 value
    print(cam.get_attribute_value("exposure_time")) # 等价于前述的 cam.cav["exposure_time"]
    #  cam.clear_acquisition() # docstring: Clear the acquisition settings. 包括清空 buffer。在 pylablib demo 代码中没有出现过，貌似可以作为衣蛾 sanity check 函数
    # cam.close() # the good'ol close. 用 with 语句时完全用不着
    # cam.dcamwait # Obscure stuff, Idk what it is. It returns `CDCAMWAIT_OPEN(supportevent=14103, hwait=2574656206000)`. BTW This is not a method, it's type is CDCAMWAIT_OPEN, whatever it means.
    # cam.dv # obscure stuff. it's an "ItemAccessor" including getter/setter/deleter
    print(cam.get_acquisition_parameters()) # self-evident
    for key, val in list(cam.get_all_attribute_values().items())[:3]: # cam.cav 全选版本， 返回一个字典, preview 前 3 个
        print(key, "||",val)
    # cam.get_all_attributes() # 等价于前述的 cam.attributes

#%%
