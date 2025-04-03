#%% 把 dir(cam) 能干的事情全部试一次
import pylablib as pll
from pylablib.devices import DCAM # gives error if dll is not found. The dll is by default in system32 folder and automatically found. if not, then use code `pll.par["devices/dlls/dcamapi"] = "path/to/dlls"`
with DCAM.DCAMCamera() as cam:
    print(cam.acquisition_in_progress()) # 返回 True/False. docstring: Check if acquisition is in progress
    ## cam.apply_settings() # takes a key-val setting dict
    assert cam.attributes == cam.get_all_attributes() # 这两个字典是完全相同的，seems not pythonic, might prefer the shorter code
    for e in list(cam.attributes.items())[:3]: print(e) # preview 前 3 个特性。min/max 等有用数值给出，但是 value 不给出
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
    ##  cam.clear_acquisition() # docstring: Clear the acquisition settings. 包括清空 buffer。在 pylablib demo 代码中没有出现过，貌似可以作为衣蛾 sanity check 函数
    ## cam.close() # the good'ol close. 用 with 语句时完全用不着
    ## cam.dcamwait # Obscure stuff, Idk what it is. It returns `CDCAMWAIT_OPEN(supportevent=14103, hwait=2574656206000)`. BTW This is not a method, it's type is CDCAMWAIT_OPEN, whatever it means.
    ## cam.dv # obscure stuff. it's an "ItemAccessor" including getter/setter/deleter
    print(cam.get_acquisition_parameters()) # self-evident, but returns None by default, not sure what it includes yet
    for e in list(cam.get_all_attribute_values(enum_as_str=True).items())[:3]: print(e) # cam.cav 全选版本， 返回一个字典, preview 前 3 个
    ## cam.get_all_attributes() # 等价于前述的 cam.attributes
    print(cam.get_all_readout_speeds()) # 返回一个 list： ['slow', 'fast']
    print(cam.get_all_trigger_modes()) # 返回一个 list： ['int', 'ext', 'software', 'master_pulse']
    ## print(cam.get_attribute("exposure_time")) # 等价于之前的 cam.ca
    ## print(cam.get_attribute_value("exposure_time")) # 等价于之前的 cam.cav。 显然， 本行和上一行的方法都是常用的， 因此有 ca， cav 这样的简写形式. cam.get_attribute_value 的唯一好处是， 在 attribute 有字符串数值时，可以用 enum_as_str=True 来返回字符串， 这一点 cam.cav 做不到
    print(cam.get_data_dimensions()) # 返回一个 tuple， 默认为 (2304, 4096)， 会随着 roi 的设定而变化. c.f. cam.get_detector_size
    print(cam.get_defect_correct_mode()) # 默认返回 True， 貌似会实时 interpolate 不好的像素，可能对 readout speed 有影响
    print(cam.get_detector_size()) # 返回 tuple (4096, 2304)，永远不变。 c.f. cam.get_data_dimensions
    print(cam.get_device_info()) # brand, S/N, etc.
    ## all possible outputs of cam.get_devices_variable():
    print(cam._device_vars.keys())  # cam.get_devices_variable() 接受的 key 来自于弱私有字典 _device_vars. 其中只有三个 keys。每个 key 对应的 val 又是一个字典。以下 每个。 以下 print 这三个字典的所有 key||val 内容， 也就是所谓的 device variables。这些 variables 有些和 cam.get_all_attribute_values 的 key， val 是重合的, 比如 "exposure_time"。但有些只有 key 重合， 比如这里的 trigger_mode 是 int， 而 cam.get_all_attribute_values() 给出的 trigger_mode 是 NORMAL
    print("===settings==")
    for e in cam._device_vars["settings"].items(): print(e[0], "||", cam.get_device_variable(e[0]))
    print("===status==")
    for e in cam._device_vars["status"].items(): print(e[0], "||", cam.get_device_variable(e[0]))
    print("===info==")
    for e in cam._device_vars["info"].items(): print(e[0], "||", cam.get_device_variable(e[0]))
    ## print(cam.get_exposure()) # 完全等价于 cam.cav["exposure_time"] 以及 cam.get_device_variable("exposure")
    print(cam.get_ext_trigger_parameters()) # 返回 tuple (<inversion>, <delay>)
    print(cam.get_frame_format()) # 默认 "list"， 可选项还有 array, chunks, 有可能影响性能
    print(cam.get_frame_info_fields()) # 返回 ['frame_index', 'framestamp', 'timestamp_us', 'camerastamp', 'position_left', 'position_top', 'pixeltype']
    print(cam.get_frame_info_format()) # "namedtuple" by default, options include dict, list, array, see doctstring for pros and cons if you care
    print(cam.get_frame_info_period()) # 一个整数 n，默认为 1. 设置为 None 可以完全不读取 frame info。设置为 n 则每 n 帧读一次 frame info
    print(cam.get_frame_period()) # 只在 internal trigger mode 中有用， 两帧之间的时间
    print(cam.get_frame_readout_time()) # idk, 默认等于 cam.get_frame_period()
    print(cam.get_frame_timings()) # 返回 (exposure, frame_period)， 默认 TAcqTimings(exposure=0.0082944, frame_period=0.0564984)
    print(cam.get_frames_status()) # 默认返回 TFramesStatus(acquired=0, unread=0, skipped=0, buffer_size=0)
    print(cam.get_full_info()) # 目测和之前的 ===info== 内容一致
    print(cam.get_full_status()) # 目测和之前的 ===status== 内容一致
    print(cam.get_image_indexing()) # 默认 rct （ROW, COL, from the TOP），可选项为 xyt
    print(cam.get_new_images_range()) # returns None by default coz no image
    print(cam.get_readout_speed()) # 返回 "slow" or "fast"
    print(cam.get_roi()) # 默认返回 (0, 4096, 0, 2304, 1, 1)， 也就是整个 detector size， binning size 为 1
    print(cam.get_roi_limits()) # 返回 (TAxisROILimit(min=4, max=4096, pstep=4, sstep=4, maxbin=4), TAxisROILimit(min=4, max=2304, pstep=4, sstep=4, maxbin=4))
    print(cam.get_settings()) # 目测和之前的 ===settings== 内容一致
    print(cam.get_status()) # acquisition status, Can be "busy" (capturing in progress), "ready" (ready for capturing), "stable" (not prepared for capturing), "unstable" (can't be prepared for capturing), or "error" (some other error).
    print(cam.get_transfer_info()) # Return tuple (last_buff, frame_count), where last_buff is the index of the last filled buffer, and frame_count is the total number of acquired frames.
    print(cam.get_trigger_mode()) # int/ext/software. 用相应的 setter 时，它实际上改变的 attr 是 trigger_source 而不是 trigger_mode。要改变 trigger_mode, 可以用 e.g. cam.cav["trigger_mode"] = 6
    # cam.grab() # rich docstring, read when in doubt
    print(cam.handle) # 貌似是用于 debug 的 handle, 返回 2591893199624
    print(cam.idx) # cam index
    print(cam.is_acquisition_setup()) # True/False to say if camera acquisition is set up. False by default
    print(cam.is_opened()) # self-evident
    # cam.open() # self-evident
    # cam.pausing_acquisition() # a CONTEXT MANAGER. i.e. to be used with `with`. rich doctstring, read when in doubt
    # cam.read_multiple_images # rich docstring
    # cam.read_newest_image() # get newest in buffer
    # cam.read_oldest_image() # get oldest in buffer, can be toggled to return (frame, info)
    # cam.send_software_trigger() # self-evident
    # cam.set_all_attribute_values()  # Set values of all attribute in the given dictionary
    # cam.set_attribute_value # probably equivalent to cam.cav[<key>]=val
    # cam.set_defect_correct_mode() # accepts True/False, default is True. a wrapper for self.set_attribute_value("DEFECT CORRECT MODE")
    # cam.set_device_variable # c.f. cam.get_devices_variable
    # cam.set_exposure() # a wrapper for `self.cav["EXPOSURE TIME"]=exposure`
    # cam.set_frame_format # Set format for the returned images. list/array/chunks
    # cam.set_frame_info_format # c.f. get_frame_info_format
    # cam.set_frame_info_period # c.f. get_frame_info_period
    # cam.set_image_indexing # c.f. get_image_indexing
    # cam.set_readout_speed # c.f. get_readout_speed. a wrapper for cam.set_attribute_value("READOUT SPEED",speed,error_on_missing=False)
    # cam.set_roi # c.f. get_roi. This is a wrapper for a host of cav settings, see the code
    # cam.set_trigger_mode # c.f. get_trigger_mode. a wrapper for self.cav["TRIGGER SOURCE"]=mode
    # cam.setup_acquisition # see https://pylablib.readthedocs.io/en/latest/devices/cameras_basics.html#acquisition-loop
    # cam.setup_ext_trigger # c.f. get_ext_trigger_parameters
    # cam.snap # a wrapper for grab. grab can return multiple shots, while snap returns one
    # cam.start_acquisition # see https://pylablib.readthedocs.io/en/latest/devices/cameras_basics.html#acquisition-loop
    # cam.stop_acquisition # see https://pylablib.readthedocs.io/en/latest/devices/cameras_basics.html#acquisition-loop
    # cam.wait_for_frame # see https://pylablib.readthedocs.io/en/latest/devices/cameras_basics.html#acquisition-loop




    





#%%
