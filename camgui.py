#%%
# pyright: reportRedeclaration=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportArgumentType=false
"""
在代码顺序上, 永远先创建 item (e.g. dpg.add_button()), 再配置 item (def callback, bind callback, etc.)
不同 item 设置的区块之间用 `#====` 分隔, 保证特定 item 的所有设置永远集中于一个区块之内, 不要分散在四处
context manager 之间不用 `#====` 分隔, 因为有自然的缩进保证了识别度
item 和 (创建 containter item 的) context manager 之间用 `#====` 分隔
item 常数用首字母小写的驼峰命名 e.g. myItem. 其他任何变量都不能用此驼峰命名 (类用首字母大写的驼峰命名, e.g. MyClass)
cam 将会是全局变量, 由 callback 创建
"""
from pathlib import Path
from typing import Callable, List, Dict
import dearpygui.dearpygui as dpg
from pylablib.devices import DCAM
import threading
import time
import math
import tifffile
from camguihelper import gui_open_awg, FrameDeck, fworker_flag_watching_acq
from camguihelper.core import _log, _update_hist, _dummy_fworker_flag_watching_acq
from camguihelper.dirhelper import mkdir_session_frames
from camguihelper.dpghelper import (
    do_bind_my_global_theme,
    do_initialize_chinese_fonts,
    do_extend_add_button,
    toggle_checkbox_and_disable,
    factory_cb_yn_modal_dialog)

controller = None # controller always has to exist, we can't wait for it to be created by a callback (like `cam`), since it is the argument of the func `start_flag_watching_acq` (and ultimately, the required arg of ZYL func `feed_AWG`) that runs in the thread thread_acq. When awg is off, `controller` won't be used and won't be created either, but the `controller` var still has to exist (as a global variable because I deem `controller` suitable to be a global var) as a formal argument (or placeholder) of `start_flag_watching_acq`. This is more or less an awkward situation because I want to put `start_flag_watching_acq` in a module file (where the functions do not have access to working script global vars), not in the working script. Essentailly, the func in a module py file has no closure access to the global varibles in the working script, unless I choose to explicitly pass the working script global var as an argument to the imported func
frame_deck = FrameDeck() # the normal empty frame_deck creation

# frame_deck = FrameDeck(flist) # the override to import fake data

dpg.create_context()
winCtrlPanels = dpg.generate_uuid() # need to generate win tags first thing to work with init file
winFramePreview = dpg.generate_uuid()
winHist = dpg.generate_uuid()
winTgtArr = dpg.generate_uuid()
dpg.configure_app(#docking = True, docking_space=True, docking_shift_only=True,
                  init_file = "dpginit.ini", )

do_bind_my_global_theme()
_, bold_font, large_font = do_initialize_chinese_fonts()
toggle_theming_and_enable = do_extend_add_button()
myCmap = dpg.mvPlotColormap_Viridis


dpg.create_viewport(title='camera', 
                    width=1460, height=1020, x_pos=0, y_pos=0, clear_color=(0,0,0,0),
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

with dpg.viewport_menu_bar():
    with dpg.menu(label="Windows"):
        """
        TODO 用 `check` kwarg 明确指示窗口显示状态
        """
        dpg.add_menu_item(label="显示控制面板")
        def _show_and_highlight_win(*cbargs):
            dpg.configure_item(winCtrlPanels, show=True, collapsed = False)
            dpg.focus_item(winCtrlPanels)
        dpg.set_item_callback(dpg.last_item(), _show_and_highlight_win)
        #=============================
        dpg.add_menu_item(label="显示预览帧窗口")
        def _show_and_highlight_win(*cbargs):
            dpg.configure_item(winFramePreview, show=True, collapsed = False)
            dpg.focus_item(winFramePreview)
        dpg.set_item_callback(dpg.last_item(), _show_and_highlight_win)
        #=============================
        dpg.add_menu_item(label="显示直方图窗口")
        def _show_and_highlight_win(*cbargs):
            dpg.configure_item(winHist, show=True, collapsed = False)
            dpg.focus_item(winHist)
        dpg.set_item_callback(dpg.last_item(), _show_and_highlight_win)
    dpg.add_menu_item(label = "软件信息")
    dpg.set_item_callback(dpg.last_item(),
                            factory_cb_yn_modal_dialog(
                                dialog_text=
                                """\
camgui 1.3-pre for A105
作者: 吴海腾, 张云龙
repo: https://github.com/ltmsyvag/camera
                                """, 
                                win_label="info", just_close=True))

with dpg.window(label= "控制面板", tag = winCtrlPanels):
    with dpg.group(label = "col panels", horizontal=True):
        with dpg.child_window(label = "cam panel", width=190):
            _wid, _hi = 175, 40
            togCam = dpg.add_button(
                width=_wid, height=_hi, user_data={
                    "is on" : False, 
                    "off label" : "相机已关闭",
                    "on label" : "相机已开启",
                    })
            dpg.bind_item_font(togCam, large_font)
            @toggle_theming_and_enable("expo and roi fields", "acquisition toggle")
            def _cam_toggle_cb_(__, _, user_data):
                state = user_data["is on"] 
                next_state = not state # state after toggle
                global cam
                if next_state:
                    if "cam" not in globals():
                        cam = DCAM.DCAMCamera()
                    if cam.is_opened():
                        cam.close()
                    cam.open()
                    print("cam is opened")
                    expFieldValInMs = dpg.get_value(fldExposure) 
                    cam.set_exposure(expFieldValInMs*1e-3)
                    expoCamValInS = cam.cav["exposure_time"]
                    dpg.set_value(fldExposure, expoCamValInS*1e3)
                    
                    do_set_cam_roi_using_6fields_roi()
                    do_set_6fields_roi_using_cam_roi()
                else:
                    cam.close() # type: ignore
                    # cam = None # commented, because I actually want to retain a closed cam object after toggling off the cam, for cam checks that might be useful
            @toggle_theming_and_enable("expo and roi fields", "acquisition toggle")
            def _dummy_cam_toggle_cb_(_, __, user_data):
                state = user_data["is on"]
                next_state = not state # state after toggle
                if next_state:
                    time.sleep(0.5)
                else:
                    time.sleep(0.5)

            dpg.set_item_callback(togCam,_cam_toggle_cb_)
            #===============================================================
            togAcq = dpg.add_button(tag="acquisition toggle", enabled=False,
                width=_wid, height=_hi, user_data={
                    "is on" : False, 
                    "off label" : "触发采集已停止",
                    "on label" : "触发采集进行中",
                    "acq thread flag": threading.Event(),
                    "acq thread": None,
                    })
            @toggle_theming_and_enable(
                    "expo and roi fields", togCam,
                    "awg panel",
                    "target array binary text input",
                    on_and_enable= False)
            def _toggle_acq_cb_(sender, _, user_data):
                state = user_data["is on"]
                next_state = not state
                flag = user_data["acq thread flag"]
                if next_state:
                    thread_worker = threading.Thread(target=fworker_flag_watching_acq, args=(cam, flag, frame_deck, controller))
                    user_data["acq thread"] = thread_worker
                    flag.set()
                    thread_worker.start()
                else:
                    thread_worker = user_data["acq thread"]
                    flag.clear()
                    thread_worker.join()
                    user_data["acq thread"] = None # this is probably a sanity code, can do without
                    # cam.stop_acquisition()
                    # cam.set_trigger_mode("int")
                    # print("acq stopped")
                # dpg.set_item_user_data(sender, user_data) # the decor saves the user_data so I might not need to explicitly save it at all       
            @toggle_theming_and_enable(
                    "expo and roi fields", togCam,
                    "awg panel",
                    "target array binary text input",
                    on_and_enable= False)
            def _dummy_toggle_acq_cb(sender, _ , user_data):
                state = user_data["is on"]
                next_state = not state
                flag = user_data["acq thread flag"]
                if next_state:
                    thread_worker = threading.Thread(
                        target=_dummy_fworker_flag_watching_acq, args=(flag, frame_deck))
                    user_data["acq thread"] = thread_worker
                    flag.set()
                    thread_worker.start()
                else:
                    thread_worker = user_data["acq thread"]
                    flag.clear()
                    thread_worker.join()
                    user_data["acq thread"] = None
                    # print("acq stopped")
                # dpg.set_item_user_data(sender, user_data)

            dpg.bind_item_font(togAcq, large_font)
            dpg.set_item_callback(togAcq, _toggle_acq_cb_)
            #==============================
            with dpg.child_window(height=122,no_scrollbar=True) as _cw:
                with dpg.group(horizontal=True):
                    dpg.add_text("参数文件夹:")
                    ttpkwargs = dict(delay=1, hide_on_activity= True)
                    with dpg.tooltip(dpg.last_item(), **ttpkwargs): # type: ignore
                        dpg.add_text("当前面板中所有的参数在触发采集开始时\n会被保存到这个文件夹")
                    dpg.add_text("CA1")
                    dpg.bind_item_font(dpg.last_item(), large_font)
                #===================================
                with dpg.group(horizontal=True):
                    dpg.add_text("帧文件夹:")
                    with dpg.tooltip(dpg.last_item(), **ttpkwargs): # type: ignore
                        dpg.add_text("当前采集的所有帧文件(tiff)\n会被保存到这个文件夹")
                    _color = (255,0,255)
                    dpg.add_text("0000", color= _color)
                    dpg.bind_item_font(dpg.last_item(), large_font)
                dpg.add_button(label="新 帧文件夹", callback=mkdir_session_frames)
            with dpg.theme() as _thm:
                with dpg.theme_component(dpg.mvChildWindow):
                    dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (0,0,0))
            dpg.bind_item_theme(_cw, _thm)
            #====================================
            with dpg.group(tag = "expo and roi fields", enabled=False):
                dpg.add_text("exposure time (ms):")
                fldExposure = dpg.add_input_float(
                    width = 120, step=0, format="%.4f",
                    default_value= 100)
                def _set_cam_exposure(_, app_data, __): # the app_data in this case is the same as dpg.get_value(fldExposure)
                    time_in_ms = app_data
                    cam.set_exposure(time_in_ms*1e-3)
                dpg.set_item_callback(fldExposure, _set_cam_exposure)
                with dpg.item_handler_registry() as _ihrUpdateFldExposureOnLeave:
                    def _cam_updates_fldExposure(*cbargs):
                        cam_internal_expo_in_ms = cam.cav["exposure_time"] * 1e3
                        dpg.set_value(fldExposure, cam_internal_expo_in_ms)
                    dpg.add_item_deactivated_after_edit_handler(callback= _cam_updates_fldExposure)
                dpg.bind_item_handler_registry(fldExposure, _ihrUpdateFldExposureOnLeave)
                #==下面的 6 roi fields 由于在 cam 中必须同时 update, 因此其共用一个 callback. 我们将相关 field items 设置代码放在一个区块内====
                dpg.add_spacer(height=10)
                dpg.add_separator(label="ROI")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): # type: ignore
                        dpg.add_text("max h 4096, max v 2304")
                dpg.add_text("h start & h length:")
                _indent = 20
                fldsROIh = dpg.add_input_intx(size=2, indent= _indent,width=100, default_value=[1352, 240,0,0])
                dpg.add_text("v start & v length:")
                fldsROIv = dpg.add_input_intx(size=2, indent = _indent ,width=dpg.get_item_width(fldsROIh), default_value=[948,240,0,0]) # type: ignore
                dpg.add_text("h binning & v binning")
                fldsBinning = dpg.add_input_intx(size=2, indent = _indent ,width=dpg.get_item_width(fldsROIh), default_value=[1,1,0,0]) # type: ignore
                def do_set_cam_roi_using_6fields_roi():
                    hstart, hwid, *_ = dpg.get_value(fldsROIh)
                    vstart, vwid, *_ = dpg.get_value(fldsROIv)
                    hbin, vbin, *_ = dpg.get_value(fldsBinning)
                    cam.set_roi(hstart, hstart+hwid, vstart, vstart+vwid, hbin, vbin)
                def do_set_6fields_roi_using_cam_roi():
                    hstart, hend, vstart, vend, hbin, vbin = cam.get_roi()
                    dpg.set_value(fldsROIh,[hstart, hend-hstart,0,0])
                    dpg.set_value(fldsROIv,[vstart, vend-vstart,0,0])
                    dpg.set_value(fldsBinning,[hbin, vbin,0,0])
                with dpg.item_handler_registry(tag="on leaving 6 ROI fields") as _irhUpdate6FlsOnLeave:
                    dpg.add_item_deactivated_after_edit_handler(callback=do_set_6fields_roi_using_cam_roi)
                for _item in [fldsROIh, fldsROIv, fldsBinning]:
                    dpg.set_item_callback(_item, do_set_cam_roi_using_6fields_roi)
                    dpg.bind_item_handler_registry(_item, _irhUpdate6FlsOnLeave)
            dpg.add_separator(label="log")
            winLog = dpg.add_child_window(tag = "log window")
            # dpg.add_button(label="msg", before=winLog, callback = lambda : push_log("hellohellohellohellohellohellohellohellohellohellohellohellohello"))
            # dpg.add_button(label="error", before=winLog, callback = lambda : push_log("hell", is_error=True))
        with dpg.child_window(label = "awg panel"):
            with dpg.group(tag = "awg panel"):
                togAwg = dpg.add_button(tag = "AWG toggle",
                    width=150, height=40, user_data={
                        "is on" : False, 
                        "off label" : "AWG 已关闭",
                        "on label" : "AWG 已开启",
                        })
                dpg.bind_item_font(togAwg, large_font)
                @toggle_theming_and_enable()
                def _awg_toggle_cb_(_,__,user_data):
                    global raw_card, controller
                    state = user_data["is on"]
                    next_state = not state
                    if next_state:
                        raw_card, controller = gui_open_awg() # raw_card is opened upon being returned by gui_open_awg()
                    else:
                        raw_card.close() # type: ignore
                        controller = None # controller always has to exist, since its the argument of the func start_acqloop that runs in the thread thread_acq
                dpg.set_item_callback(togAwg, _awg_toggle_cb_)
                dpg.add_separator()
                _width=100
                _spcheight=10
                dpg.add_input_intx(label= "x1 y1", tag= "x1 y1", size=2, width=_width, default_value = [36,23,0,0])
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("基矢起点 x y 坐标") #type:ignore
                dpg.add_input_intx(label= "x2 y2", tag= "x2 y2", size=2, width=_width, default_value = [124,25,0,0])
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("x 方向基矢 x y 坐标") #type:ignore
                dpg.add_input_intx(label= "x3 y3", tag= "x3 y3", size=2, width=_width, default_value = [34,112,0,0])
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("y 方向基矢 x y 坐标") #type:ignore
                dpg.add_input_intx(label= "nx ny", tag= "nx ny", size=2, width=_width, default_value = [16,16,0,0])
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("阵列 x y 方向尺寸") #type:ignore
                dpg.add_input_intx(label= "x0 y0", tag= "x0 y0", size=2, width=_width, default_value = [34,21,0,0])
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("选择起点") #type:ignore
                dpg.add_input_intx(label= "rec_x rec_y", tag= "rec_x rec_y", size=2, width=_width, default_value=[4,4,0,0])
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("每个点位选择统计光子数的 mask 大小") #type:ignore
                dpg.add_input_int(label="count_threshold",tag="count_threshold",step=0, width=_width/2, default_value=30) #type:ignore
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("判断是否有光子的阈值") #type:ignore
                dpg.add_input_int(label="n_packed",tag="n_packed",step=0, width=_width/2, default_value=3) #type:ignore
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("决定了每次移动的原子数") #type:ignore
                dpg.add_spacer(height=_spcheight)
                dpg.add_text("start_frequency_on_row(col)")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("行(列)方向的起始频率，即第一行(列)对应的频率") #type:ignore
                dpg.add_input_floatx(tag = "start_frequency_on_row(col)", size=2, width=_width*1.2, default_value=[90.8,111.4,0,0], label="MHz") #type:ignore
                dpg.add_text("end_frequency_on_row(col)")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("行(列)方向的终止频率") #type:ignore
                dpg.add_input_floatx(tag = "end_frequency_on_row(col)", size=2, width=_width*1.2, default_value=[111.3,90.8,0,0], label= "MHz") #type:ignore
                dpg.add_text("start_site_on_row(col)")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("行(列)方向的原子起始坐标") #type:ignore
                dpg.add_input_intx(tag = "start_site_on_row(col)", size=2, width=_width, default_value=[0,0,0,0])
                dpg.add_text("end_site_on_row(col)")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("行(列)方向的原子终止坐标") #type:ignore
                dpg.add_input_intx(tag = "end_site_on_row(col)", size=2, width=_width, default_value=[15,15,0,0])
                dpg.add_spacer(height=_spcheight)
                dpg.add_input_int(label="num_segments", tag="num_segments",step=0, width=_width/2, default_value=16) #type:ignore
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("决定了 s 曲线 ramp 的平滑程度") #type:ignore
                dpg.add_input_float(label="power_ramp_time (ms)", tag="power_ramp_time (ms)",step=0, width=_width/2, default_value=4) #type:ignore
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("功率 ramp 的时间") #type:ignore
                dpg.add_input_float(label="move_time (ms)", tag="move_time (ms)", step=0, width=_width/2, default_value=2) #type:ignore
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("频率 ramp 的速度，也就是单个光镊移动的速度") #type:ignore
                dpg.add_spacer(height=_spcheight)
                dpg.add_text("percentage_total_power_for_list")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("送入aod每个轴的最大功率，是一个百分数，代表最终上升到awg设定最大电平的多少") #type:ignore
                dpg.add_input_float(tag = "percentage_total_power_for_list", step=0, width=_width/2, default_value=0.5) #type:ignore
                dpg.add_input_text(label = "ramp_type", tag = "ramp_type", width=_width, default_value="5th-order")
                with dpg.tooltip(dpg.last_item(), **ttpkwargs): dpg.add_text("决定了扫频的曲线形式") #type:ignore
                dpg.add_spacer(height=_spcheight)
                _btn = dpg.add_button(label="设置目标阵列")
                dpg.set_item_callback(_btn, # strange, dpg.last_item() does not work here
                                      lambda : dpg.show_item(winTgtArr)
                                    #   lambda : dpg.configure_item(winTgtArr, show=True)
                                      )

with dpg.window(label = "设置目标阵列", tag = winTgtArr,
                pos = (200,200), width = 430, height=430):
    dpg.set_frame_callback(1,lambda: dpg.configure_item(winTgtArr, show=False)) # hide win on 1st frame, not during context creation, else this hidden-by-default window's size won't be remembered by init file
    dpg.add_input_text(tag = "target array binary text input",
        multiline= True, width=-1,height=-1,
        default_value="""\
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0""")


with dpg.file_dialog( # file dialog 就是一个独立的 window, 因此在应该在 root 定义, 与其他 window 内的元素在形式上解耦
    directory_selector=False, show=False, modal=True,
    tag="file dialog", width=700 ,height=400) as fileDialog:
    dpg.add_file_extension("", color = (150,255,150,255)) # 让文件夹显示为绿色
    dpg.add_file_extension(".*") # 显示 _select_all
    # dpg.add_file_extension(".tif")
    # dpg.add_file_extension(".tiff")
    dpg.add_file_extension("tiff files (*.tif *.tiff){.tif,.tiff}") # the {} part is what the file dialog really parses, others are for human eyes
    def _ok_cb_(_, app_data, __)->None:
        """
        选择 4 个 tif 文件时的 app_data: {
        'file_path_name': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\4 files Selected.tif', 
        'file_name': '4 files Selected.tif', 
        'current_path': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images', 
        'current_filter': '.tif', 
        'min_size': [100.0, 100.0], 
        'max_size': [30000.0, 30000.0], 
        'selections': {
            'Image_0093.tif': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\Image_0093.tif', 
            'Image_0094.tif': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\Image_0094.tif',
            'Image_0095.tif': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\Image_0095.tif',
            'Image_0096.tif': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\Image_0096.tif'}}, 
        
        选择 1 个文件时的 app_data: {
        'file_path_name': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\Image_00101.tif',
        'file_name': 'Image_00101.tif', 
        'current_path': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images', 
        'current_filter': '.tif', 
        'min_size': [100.0, 100.0],
        'max_size': [30000.0, 30000.0], 
        'selections': {'Image_00101.tif': 'c:\\Users\\DELL\\Desktop\\baslercam\\20by20 images\\Image_00101.tif'}}
        """
        global frame_deck
        fname_dict = app_data["selections"]
        if "_select_all" in fname_dict:
            dpath = Path(app_data["current_path"])
            frame_list = [tifffile.imread(e) for e in dpath.iterdir() if e.suffix in [".tif", ".tiff"]]       
        else:
            frame_list = [tifffile.imread(e) for e in fname_dict.values()]          
        for e in frame_list:
            frame_deck.append(e)
        frame_deck.plot_frame_dwim()
    dpg.set_item_callback(fileDialog, _ok_cb_)


with dpg.window(label = "帧预览", tag=winFramePreview,
                height=700, width=700
                ):
    # dpg.add_button(label="hello", callback=lambda: frame_deck._update_session_data_dir())
    with dpg.menu_bar():
        with dpg.menu(label = "内存中的帧"):
            dpg.add_menu_item(label = "保存当前帧")
            dpg.set_item_callback(dpg.last_item(), lambda: frame_deck.save_cid_frame())
            #=============================
            dpg.add_menu_item(label = "保存所有帧")
            dpg.set_item_callback(dpg.last_item(), lambda: frame_deck.save_deck())
            #================================
            dpg.add_menu_item(label = "清空所有帧")
            def _on_confirm(sender):
                frame_deck.clear()
                dpg.delete_item(
                    dpg.get_item_parent(dpg.get_item_parent(sender))
                    )  # Close the modal after confirming
            dpg.set_item_callback(dpg.last_item(),
                                    factory_cb_yn_modal_dialog(cb_on_confirm=_on_confirm, dialog_text="确认要清空内存中的所有帧吗?"))
        #=========================
        dpg.add_menu_item(label = "载入帧", callback=lambda: dpg.show_item(fileDialog))
        with dpg.menu(label = "热图主题"):
            def factory_cb_bind_heatmap_cmap(cmap: int)-> Callable:
                def cb_bind_heatmap_theme(sender, *args) ->None:
                    dpg.bind_colormap(frameColBar, cmap)
                    dpg.bind_colormap(framePlot, cmap)
                    for xax, *_ in frame_deck.llst_items_dupe_maps:
                        tagPlot = dpg.get_item_parent(xax)
                        dpg.bind_colormap(tagPlot, cmap)
                    lst_other_menu_items: Dict[int, List] = dpg.get_item_children(dpg.get_item_parent(sender))[1]
                    lst_other_menu_items.remove(sender) # type: ignore
                    dpg.set_value(sender, True)
                    for item in lst_other_menu_items:
                        dpg.set_value(item, False)
                return cb_bind_heatmap_theme
            
            dpg.add_menu_item(label="Deep", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Deep), check=True)
            dpg.add_menu_item(label="Dark", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Dark), check=True)
            dpg.add_menu_item(label="Pastel", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Pastel), check=True)
            dpg.add_menu_item(label="Paired", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Paired), check=True)
            dpg.add_menu_item(label="Viridis", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Viridis), check=True, default_value=True)
            dpg.add_menu_item(label="Plasma", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Plasma), check=True)
            dpg.add_menu_item(label="Hot", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Hot), check=True)
            dpg.add_menu_item(label="Cool", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Cool), check=True)
            dpg.add_menu_item(label="Pink", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Pink), check=True)
            dpg.add_menu_item(label="Jet", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Jet), check=True)
            dpg.add_menu_item(label="Twilight", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Twilight), check=True)
            dpg.add_menu_item(label="RdBu", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_RdBu), check=True)
            dpg.add_menu_item(label="BrBG", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_BrBG), check=True)
            dpg.add_menu_item(label="PiYG", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_PiYG), check=True)
            dpg.add_menu_item(label="Spectral", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Spectral), check=True)
            dpg.add_menu_item(label="Greys", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Greys), check=True)
            def _make_reverse_cmap(tagCmap: int, ncolors: int=11)->list:
                """
                reverse a dpg builtin cmap scheme. usually the continuous heatmaps have 11 colors, except for grey (2 colors)
                """
                series = [dpg.get_colormap_color(tagCmap, i) for i in range(ncolors)]
                series = [
                    [int(r*255), int(g*255), int(b*255), int(a*255)] for (r,g,b,a) in series
                    ]
                series.reverse()
                return series
            with dpg.colormap_registry():
                dpg.mvPlotColormap_Viridis_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Viridis), qualitative=False)
                dpg.mvPlotColormap_Plasma_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Plasma), qualitative=False)
                dpg.mvPlotColormap_Hot_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Hot), qualitative=False)
                dpg.mvPlotColormap_Cool_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Cool), qualitative=False)
                dpg.mvPlotColormap_Pink_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Pink), qualitative=False)
                dpg.mvPlotColormap_Jet_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Jet), qualitative=False)
                dpg.mvPlotColormap_Twilight_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Twilight), qualitative=False)
                dpg.mvPlotColormap_RdBu_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_RdBu), qualitative=False)
                dpg.mvPlotColormap_BrBG_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_BrBG), qualitative=False)
                dpg.mvPlotColormap_PiYG_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_PiYG), qualitative=False)
                dpg.mvPlotColormap_Spectral_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Spectral), qualitative=False)
                dpg.mvPlotColormap_Greys_r = dpg.add_colormap(_make_reverse_cmap(dpg.mvPlotColormap_Greys, ncolors=2), qualitative=False)
            dpg.add_menu_item(label="Viridis_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Viridis_r), check=True)
            dpg.add_menu_item(label="Plasma_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Plasma_r), check=True)
            dpg.add_menu_item(label="Hot_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Hot_r), check=True)
            dpg.add_menu_item(label="Cool_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Cool_r), check=True)
            dpg.add_menu_item(label="Pink_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Pink_r), check=True)
            dpg.add_menu_item(label="Jet_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Jet_r), check=True)
            dpg.add_menu_item(label="Twilight_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Twilight_r), check=True)
            dpg.add_menu_item(label="RdBu_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_RdBu_r), check=True)
            dpg.add_menu_item(label="BrBG_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_BrBG_r), check=True)
            dpg.add_menu_item(label="PiYG_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_PiYG_r), check=True)
            dpg.add_menu_item(label="Spectral_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Spectral_r), check=True)
            dpg.add_menu_item(label="Greys_r", callback= factory_cb_bind_heatmap_cmap(dpg.mvPlotColormap_Greys_r), check=True)
    #=========================================   
    fldSavePath = dpg.add_input_text(tag="save path input field",
                            hint="path to save tiff, e.g. C:\\Users\\username\\Desktop\\"
                            # ,callback=frame_deck._make_savename_stub
                            )
    # frame_deck._make_savename_stub()
    #========================================
    dpg.add_text(tag = "frame deck display", default_value= frame_deck.memory_report())
    dpg.bind_item_font(dpg.last_item(), bold_font)
    with dpg.group(label = "热图上下限, 帧翻页", horizontal=True):
        _inputInt = dpg.add_drag_intx(tag = "color scale lims",label = "", size = 2, width=100, default_value=[0,65535,0,0], enabled=False, max_value=65535, min_value=0, clamped=True)
        with dpg.tooltip(_inputInt, **ttpkwargs): dpg.add_text("热图上下限, 最多 0-65535\n若未勾选'手动上下限', 则每次绘图自动用全帧最大/最小值作为上下限")
        def _set_color_scale(_, app_data, __):
            fmin, fmax, *_ = app_data
            # print(heatSeries)
            dpg.configure_item(frameColBar, min_scale = fmin, max_scale = fmax)
            for yax in frame_deck.get_all_tags_yaxes():
                heatmapSlot = dpg.get_item_children(yax)[1]
                if heatmapSlot:
                    heatSeries, = heatmapSlot
                    dpg.configure_item(heatSeries, scale_min = fmin, scale_max = fmax)

        dpg.set_item_callback(_inputInt, _set_color_scale)
        #===========================================
        dpg.add_checkbox(tag = "manual scale checkbox", label = "手动上下限")
        @toggle_checkbox_and_disable("color scale lims", on_and_enable=True)
        def _empty_cb(*cbargs):
            pass
        dpg.set_item_callback(dpg.last_item(), _empty_cb)
        #===============================================
        leftArr = dpg.add_button(tag = "plot previous frame", label="<", arrow=True)
        def _left_arrow_cb_(*cbargs):
            if frame_deck.cid:
                frame_deck.cid -= 1
                frame_deck.plot_cid_frame()
                dpg.set_item_label(cidIndcator, f"{frame_deck.cid}")
        dpg.set_item_callback(leftArr, _left_arrow_cb_)
        #===========================================
        cidIndcator = dpg.add_button(tag="cid indicator", label="N/A", width=40, height=29)
        with dpg.tooltip(dpg.last_item(), **ttpkwargs):
            dpg.add_text("数字是帧的 python id (从零开始)\n内存为空的时候显示 'N/A'")
        heatmap_plot_kwargs = dict(no_mouse_pos=False, height=-1, width=-1, equal_aspects=True)
        heatmap_xyaxkwargs = dict(no_gridlines = True, no_tick_marks = True)
        heatmap_xkwargs = dict(label= "", opposite=True)
        heatmap_ykwargs = dict(label= "", invert=True)
        def _dupe_heatmap():
            # xax = dpg.generate_uuid() # 在实际创建这些 items 之前就要用到它们的 tag, 故先创建此 tag
            yax = dpg.generate_uuid() 
            inputInt = dpg.generate_uuid() 
            radioBtn = dpg.generate_uuid()
            cBox = dpg.generate_uuid()
            dupe_map_items = yax, inputInt, radioBtn, cBox
            def _on_close(sender, *args):
                """
                window 的 on close callback 貌似不同于普通 callback, 只能在创建 window 时设置, 
                因此这里将这个 callback 定义在先
                """
                frame_deck.llst_items_dupe_maps.remove(dupe_map_items)
                dpg.delete_item(sender)
            with dpg.window(width=300, height=300, on_close=_on_close, label = f"#{len(frame_deck.llst_items_dupe_maps)}"):
                frame_deck.llst_items_dupe_maps.append(dupe_map_items)
                with dpg.group(horizontal=True) as _grp:
                    #==============================
                    dpg.add_input_int(width=100, tag=inputInt, max_value=0, max_clamped=True, 
                                    #   callback=_log
                                      )
                    def _cb_input_int(*args):
                        frame_deck._update_dupe_map(*dupe_map_items)
                    dpg.set_item_callback(inputInt, _cb_input_int)
                    #===============================
                    dpg.add_radio_button(("倒数帧", "正数帧"), tag=radioBtn,
                                         default_value="倒数帧", horizontal=True,
                                        #  callback=_log
                                         )
                    def _cb_radio(_, app_data, __):
                        """
                        这个 radio button 的 callback 必须放在 enclosing 的 _dupe_heatmap callback 定义中,
                        因为它需要操纵的 item 是 enclosing callback 创造的对象, 需要利用 enclosing scope 中的变量 inputInt
                        """
                        input_id = dpg.get_value(inputInt)
                        empty_deck = True if not frame_deck.cid else False
                        if empty_deck:
                            dpg.set_value(inputInt, 0)
                        else:
                            if app_data == "倒数帧": # convert forward id to backward id
                                converted_id = input_id - len(frame_deck) + 1
                            else: # convert backward id to forward id
                                converted_id = input_id + len(frame_deck) - 1 
                            dpg.set_value(inputInt, converted_id)
                        if app_data == "倒数帧": # unlim low bound, lim high bound to 0
                            dpg.configure_item(inputInt, min_clamped = False)
                            dpg.configure_item(inputInt, max_value = 0, max_clamped = True)
                        else: # unlim high bound, lim low bound to 0
                            dpg.configure_item(inputInt, max_clamped = False)
                            dpg.configure_item(inputInt, min_value = 0, min_clamped = True)
                    dpg.set_item_callback(radioBtn, _cb_radio)
                with dpg.plot(**heatmap_plot_kwargs):
                    dpg.bind_colormap(dpg.last_item(), myCmap)
                    xax = dpg.add_plot_axis(dpg.mvXAxis, **heatmap_xkwargs, **heatmap_xyaxkwargs)
                    dpg.add_plot_axis(dpg.mvYAxis, tag=yax, **heatmap_ykwargs, **heatmap_xyaxkwargs)
                    xaxlims_orig, yaxlims_orig = dpg.get_axis_limits("frame xax"), dpg.get_axis_limits("frame yax")
                    dpg.set_axis_limits(xax, *xaxlims_orig)
                    dpg.set_axis_limits(yax, *yaxlims_orig)
                    dpg.split_frame()
                    dpg.set_axis_limits_auto(xax)
                    dpg.set_axis_limits_auto(yax)
                #======================
                dpg.add_checkbox(pos = (8,62), tag = cBox) # 要画在 plot 上, 所以在 plot 后添加
                @toggle_checkbox_and_disable(_grp)
                def _toggle_id_and_avg_map_(sender, *args):
                    frame_deck._update_dupe_map(yax,inputInt, radioBtn, sender)
                dpg.set_item_callback(cBox, _toggle_id_and_avg_map_)
                with dpg.tooltip(cBox, **ttpkwargs):
                    dpg.add_text("切换单帧/平均帧")

            frame_deck.plot_cid_frame(yax)    
        dpg.set_item_callback(cidIndcator, _dupe_heatmap)
        #==========================================
        rightArr = dpg.add_button(tag = "plot next frame", label=">", arrow=True, direction=dpg.mvDir_Right)
        def _right_arrow_cb_(*cbargs):
            if frame_deck and (frame_deck.cid<len(frame_deck)-1):
                frame_deck.cid += 1
                frame_deck.plot_cid_frame()
                dpg.set_item_label(cidIndcator, f"{frame_deck.cid}")
        dpg.set_item_callback(rightArr, _right_arrow_cb_)
        # dpg.add_spacer(width = 10)
        #============================================
    with dpg.group(horizontal=True):
        frameColBar = dpg.add_colormap_scale(tag = "frame colorbar", min_scale=0, max_scale=500, 
                            height=-1
                            )
        dpg.bind_colormap(dpg.last_item(), myCmap)
        with dpg.plot(tag="frame plot",
                    query=True, query_color=(255,0,0), max_query_rects=1, min_query_rects=0,
                    **heatmap_plot_kwargs) as framePlot:
            dpg.bind_colormap(dpg.last_item(), myCmap)
            
            dpg.add_plot_axis(dpg.mvXAxis, tag = "frame xax",**heatmap_xkwargs, **heatmap_xyaxkwargs)
            frameYax = dpg.add_plot_axis(dpg.mvYAxis, tag= "frame yax", **heatmap_ykwargs, **heatmap_xyaxkwargs)
            for ax in ["frame xax", "frame yax"]:
                dpg.set_axis_limits(ax, 0, 240)
                # dpg.split_frame() # waits forever because frames are not rolling in the context creation stage
            def _do_loosen_initial_lims():
                for ax in ["frame xax", "frame yax"]:
                    dpg.set_axis_limits_auto(ax)
            dpg.set_frame_callback(2, _do_loosen_initial_lims) # seems this is the only way to set the initial limits
            def floorHalfInt(num: float) -> float: # 0.6, 0.5 -> 0.5; 0.4 -> -0.5
                return math.floor(num-0.5) + 0.5
            def ceilHalfInt(num: float) -> float: # -0.6,-0.5 -> -0.5; 0.4,0.5 ->0.5, 0.6 - > 1.5
                return math.ceil(num+0.5) - 0.5
            def _update_hist_on_query_(sender, app_data, user_data):
                """
                log geometric centers of box selected pixels
                    h->
                  #1------+
                v  |      |
                ↓  +-----#2
                app_data: (h1, v1, h2, v2)
                """
                if app_data:
                    h1, v1, h2, v2 = app_data[0]
                    hLhRvLvR = hLlim, hRlim, vLlim, vRlim = ceilHalfInt(h1), floorHalfInt(h2), ceilHalfInt(v1), floorHalfInt(v2)
                    if user_data and hLhRvLvR == user_data:
                        pass
                    else:
                        dpg.set_item_user_data(framePlot, hLhRvLvR)
                        if hLlim <= hRlim and vLlim <=vRlim: # make sure at least one pixel's geo center falls within the query rect
                            _update_hist(hLhRvLvR, frame_deck)
                else: # this is only needed for the current query rect solution for hist udpates. actions from other items cannot check app_data of this item directly (usually dpg.get_value(item) can check the app_data of an item, but not for this very special query rect coordinates app_data belonging to the heatmap plot!), so they check the user_data of this item. since I mean to stop any histogram updating when no query rect is present, then this no-rect info is given by user_data = None of the heatmap plot.
                    dpg.set_item_user_data(sender, None)
            dpg.set_item_callback(framePlot,callback=_update_hist_on_query_)
    #===本 checkbox 需要画在 plot 上面, 因此在 plot 添加
    dpg.add_checkbox(tag="toggle 积分/单张 map", pos = (85,153))
    @toggle_checkbox_and_disable(leftArr, rightArr, 
                                #  cidIndcator # commented because we want to duplicate map when the main map is showing avg frame
                                 )
    def _toggle_cid_and_avg_map_(_, app_data,__):
        if app_data:
            frame_deck.plot_avg_frame()
        else:
            frame_deck.plot_cid_frame()
    dpg.set_item_callback(dpg.last_item(), _toggle_cid_and_avg_map_)
    with dpg.tooltip(dpg.last_item(), **ttpkwargs):
        dpg.add_text("切换单帧/平均帧")
with dpg.window(label="直方图", tag=winHist, 
                width = 500, height =300):
    dpg.add_input_int(
        # pos=(80,35), 
        tag = "hist binning input",label="hist binning", width=80,
                    min_value=1, default_value=1, min_clamped=True)
    with dpg.plot(tag="hist plot", 
                #   label = "hist", 
                  height=-1, width=-1, no_mouse_pos=True):
        dpg.add_plot_axis(dpg.mvXAxis, label = "converted counts ((<frame pixel counts>-200)*0.1/0.9)")
        dpg.add_plot_axis(dpg.mvYAxis, label = "frequency", tag = "hist plot yax")

if True: # do dummy acquisition
    dpg.set_item_callback(togCam,_dummy_cam_toggle_cb_)
    dpg.set_item_callback(togAcq, _dummy_toggle_acq_cb)
    cam = None # probably needed for dummy acquisition, the same reason as needing controller = None

# dpg.show_style_editor()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# init file 在 destroy context 时保存, 因此对 init file 的 truncation 需要在 destroy context 后执行
with open("dpginit.ini") as f:
    lines = f.readlines()
lines = lines[:25] # delete line 26 and onward. 因为只记忆 4 个窗口的位置, 新创建的窗口(被 append 再 ini 文件末)都会被删掉
with open("dpginit.ini", "w") as f:
    f.writelines(lines)


# %%
