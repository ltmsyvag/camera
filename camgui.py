#%%
"""
在代码顺序上, 永远先创建 item (e.g. dpg.add_button()), 再配置 item (def callback, bind callback, etc.)
不同 item 设置的区块之间用 `#====` 分隔, 保证特定 item 的所有设置永远集中于一个区块之内, 不要分散在四处
context manager 之间不用 `#====` 分隔, 因为有自然的缩进保证了识别度
item 和 (创建 containter item 的) context manager 之间用 `#====` 分隔
item 常数用首字母小写的驼峰命名 e.g. myItem. 其他任何变量都不能用此驼峰命名 (类用首字母大写的驼峰命名, e.g. MyClass)
cam 将会是全局变量, 由 callback 创建
"""
from camguihelper import (
    FrameDeck, DupeMap, st_workerf_flagged_do_all, collect_awg_params, gui_open_awg,
    mt_producerf_polling_do_snag_rearrange_deposit,
    mp_producerf_polling_do_snag_rearrange_send, mp_passerf, consumerf_local_buffer,
    push_exception, push_log, save_camgui_json_to_savetree, camgui_ver)
from pylablib.devices import DCAM
if __name__ == '__main__':
    import numpy as np
    # from collections import deque
    from itertools import cycle
    # import pandas as pd
    import json
    import multiprocessing
    from pathlib import Path
    from typing import Callable, Dict, Tuple
    import dearpygui.dearpygui as dpg
    import threading
    import time
    import math
    import tifffile
    # from camguihelper import FrameDeck, st_workerf_flagged_do_all, collect_awg_params
    from camguihelper.core import _log, _update_hist
    from camguihelper.utils import mkdir_session_frames, session_frames_root, camgui_params_root, find_newest_daypath_in_save_tree
    from camguihelper.dpghelper import (
        do_bind_my_default_global_theme,
        do_bind_my_global_nosave_theme,
        do_initialize_chinese_fonts,
        do_extend_add_button,
        get_viewport_centerpos,
        toggle_checkbox_and_disable,
        factory_cb_yn_modal_dialog)

    controller = None # controller always has to exist, we can't wait for it to be created by a callback (like `cam`), since it is the argument of the func `start_flag_watching_acq` (and ultimately, the required arg of ZYL func `feed_AWG`) that runs in the thread thread_acq. When awg is off, `controller` won't be used and won't be created either, but the `controller` var still has to exist (as a global variable because I deem `controller` suitable to be a global var) as a formal argument (or placeholder) of `start_flag_watching_acq`. This is more or less an awkward situation because I want to put `start_flag_watching_acq` in a module file (where the functions do not have access to working script global vars), not in the working script. Essentailly, the func in a module py file has no closure access to the global varibles in the working script, unless I choose to explicitly pass the working script global var as an argument to the imported func
    frame_deck = FrameDeck() # the normal empty frame_deck creation
    dpg.create_context()
    winCtrlPanels = dpg.generate_uuid() # need to generate win tags first thing to work with init file
    winFramePreview = dpg.generate_uuid()
    winHist = dpg.generate_uuid()
    winTgtArr = dpg.generate_uuid()
    dpg.configure_app(#docking = True, docking_space=True, docking_shift_only=True,
                    init_file = "dpginit.ini", )

    do_bind_my_default_global_theme()
    _, bold_font, large_font = do_initialize_chinese_fonts()
    toggle_state_and_enable = do_extend_add_button()
    myCmap = dpg.mvPlotColormap_Viridis

    dpg.create_viewport(title='camera', 
                        width=1460, height=1020, x_pos=0, y_pos=0, clear_color=(0,0,0,0),
                        vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

    with dpg.viewport_menu_bar():
        with dpg.menu(label='Windows'):
            dpg.add_menu_item(label='显示控制面板')
            def _show_and_highlight_win(*cbargs):
                dpg.configure_item(winCtrlPanels, show=True, collapsed = False)
                dpg.focus_item(winCtrlPanels)
            dpg.set_item_callback(dpg.last_item(), _show_and_highlight_win)
            #=============================
            dpg.add_menu_item(label='显示预览帧窗口')
            def _show_and_highlight_win(*cbargs):
                dpg.configure_item(winFramePreview, show=True, collapsed = False)
                dpg.focus_item(winFramePreview)
            dpg.set_item_callback(dpg.last_item(), _show_and_highlight_win)
            #=============================
            dpg.add_menu_item(label='显示直方图窗口')
            def _show_and_highlight_win(*cbargs):
                dpg.configure_item(winHist, show=True, collapsed = False)
                dpg.focus_item(winHist)
            dpg.set_item_callback(dpg.last_item(), _show_and_highlight_win)
        with dpg.menu(label='并发方式') as menuConcurrency:
            def _set_exclusive_True(sender, *args):
                if type(sender) is str:
                    sender = dpg.get_alias_id(sender)
                lst_other_menu_items: list = dpg.get_item_children(dpg.get_item_parent(sender))[1]
                lst_other_menu_items.remove(sender)
                dpg.set_value(sender, True)
                for item in lst_other_menu_items:
                    dpg.set_value(item, False)
            _str = '无并发: 单线程采集重排绘图保存'
            mItemSingleThread = dpg.add_menu_item(tag = _str, label= _str, check=True, callback=_set_exclusive_True, default_value=True)
            _str = '双线程: 采集重排 & 绘图保存'
            mItemDualThreads = dpg.add_menu_item(tag = _str, label=_str,  check=True, callback=_set_exclusive_True)
            _str = '双进程: 采集重排 & 绘图保存'
            mItemDualProcesses = dpg.add_menu_item(tag = _str, label=_str,  check=True, callback=_set_exclusive_True)
            # print(mItemSingleThread, mItemDualThreads, mItemDualProcesses)
        with dpg.menu(label = '软件信息'):
            dpg.add_menu_item(label = '帮助')
            dpg.set_item_callback(dpg.last_item(),
                                    factory_cb_yn_modal_dialog(
                                        dialog_text=
                                        """\
添加直方图选区:
- 添加一个: ctrl + 左键

删除直方图选区:
- 删除一个: alt + 左键
- 全部删除: F11

显示/隐藏选取组编号: F12
""", 
                                        win_label='帮助', just_close=True))
            dpg.add_menu_item(label = '关于')
            dpg.set_item_callback(dpg.last_item(),
                                    factory_cb_yn_modal_dialog(
                                        dialog_text=
                                        f"""\
camgui {camgui_ver} for A105
作者: 吴海腾, 张云龙
repo: https://github.com/ltmsyvag/camera
                                        """, 
                                        win_label='info', just_close=True))
    dummy_acq = True # 假采集代码的总开关
    if dummy_acq:
        _mp_dummy_remote_buffer = multiprocessing.Queue() # mp dummy remote buffer 必须在主脚本中创建, 才能确保 mp dummy buffer feeder 和 mp producer 所用的 Queue 对象是同一个
    with dpg.window(label= '控制面板', tag = winCtrlPanels):
        with dpg.menu_bar():
            mItemLoadJson = dpg.add_menu_item(label = '载入 json', callback= lambda: dpg.show_item(jsonDialog))
        with dpg.group(label = 'col panels', horizontal=True):
            with dpg.child_window(label = "cam panel", width=190):
                _wid, _hi = 175, 40
                togCam = dpg.add_button(
                    width=_wid, height=_hi, user_data={
                        'is on' : False, 
                        'off label' : "相机已关闭",
                        'on label' : "相机已开启",
                        })
                def do_set_cam_params_by_gui():
                    expFieldValInMs = dpg.get_value(fldExposure) 
                    cam.set_exposure(expFieldValInMs*1e-3)
                    expoCamValInS = cam.cav["exposure_time"]
                    dpg.set_value(fldExposure, expoCamValInS*1e3)
                    do_set_cam_roi_using_6fields_roi()
                    do_set_6fields_roi_using_cam_roi()
                def do_cam_open_sequence():
                    global cam
                    cam = DCAM.DCAMCamera()
                    cam.open()
                    do_set_cam_params_by_gui()
                dpg.bind_item_font(togCam, large_font)
                @toggle_state_and_enable("expo and roi fields", "acquisition toggle")
                def _cam_toggle_cb_(__, _, user_data):
                    state = user_data["is on"] 
                    next_state = not state # state after toggle
                    global cam
                    if next_state:
                        do_cam_open_sequence()
                    else:
                        cam.close()
                        # cam = None # commented, because I actually want to retain a closed cam object after toggling off the cam, for cam checks that might be useful
                @toggle_state_and_enable("expo and roi fields", "acquisition toggle")
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
                        })
                @toggle_state_and_enable(
                        "expo and roi fields", togCam, mItemLoadJson,
                        "awg panel",
                        "target array binary text input", menuConcurrency,
                        on_and_enable= False)
                def _toggle_acq_cb_(sender, _, user_data):
                    state = user_data["is on"]
                    next_state = not state
                    flag = user_data["acq thread flag"] # flag for st and mt, but not for mp
                    global raw_card, controller
                    if dpg.get_value(mItemSingleThread):
                        if next_state:
                            t_worker_do_all = threading.Thread(target=st_workerf_flagged_do_all, args=(cam, flag, frame_deck, controller))
                            user_data["thread1"] = t_worker_do_all
                            flag.set()
                            t_worker_do_all.start()
                        else:
                            t_worker_do_all = user_data["thread1"]
                            flag.clear()
                            t_worker_do_all.join()
                            # user_data["thread1"] = None # this is probably a sanity code, can do without
                    elif dpg.get_value(mItemDualThreads):
                        if next_state:
                            t_producer = threading.Thread(
                                target=mt_producerf_polling_do_snag_rearrange_deposit,
                                args= (cam, flag, controller))
                            t_consumer = threading.Thread(
                                target= consumerf_local_buffer, args = (frame_deck,))
                            user_data["thread1"] = t_producer
                            user_data["thread2"] = t_consumer
                            flag.set()
                            t_producer.start()
                            t_consumer.start()
                        else:
                            t_producer = user_data["thread1"]
                            t_consumer = user_data["thread2"]
                            flag.clear()
                            t_producer.join()
                            t_consumer.join()
                    else: # dual processes
                        if next_state:
                            exposure = cam.cav["exposure time"] # 为了将这些 cam 参数 carry 到新进程中, 在关闭 cam 前, 先取得这些参数
                            hstart, hend, vstart, vend, hbin, vbin = cam.get_roi()
                            cam.close() # close everything, to allow the new process properly reopen them
                            awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"]
                            if awg_is_on:
                                raw_card.close()
                                controller = None
                            conn_sig_main, conn_sig_child = multiprocessing.Pipe()
                            conn_data_main, conn_data_child = multiprocessing.Pipe()
                            p_producer = multiprocessing.Process(
                                target =mp_producerf_polling_do_snag_rearrange_send, 
                                args=(conn_sig_child, conn_data_child,
                                      (exposure, hstart, hend, vstart, vend, hbin, vbin),
                                      awg_is_on, collect_awg_params()))
                            t_passer = threading.Thread(
                                target=mp_passerf, 
                                args = (conn_data_main, ))
                            t_consumer = threading.Thread(
                                target=consumerf_local_buffer,
                                args = (frame_deck, ))
                            user_data['signal connection'] = conn_sig_main
                            user_data["process1"] = p_producer
                            user_data["thread1"] = t_passer
                            user_data["thread2"] = t_consumer
                            p_producer.start()
                            msg = conn_sig_main.recv()
                            push_log(msg, is_good = True)
                            t_passer.start()
                            t_consumer.start()
                        else:
                            conn_sig_main = user_data['signal connection']
                            p_producer = user_data["process1"]
                            t_passer = user_data['thread1']
                            t_consumer = user_data['thread2']
                            conn_sig_main.send(None)
                            conn_sig_main.close()
                            p_producer.join()
                            t_passer.join()
                            t_consumer.join()
                            do_cam_open_sequence()
                            if dpg.get_item_user_data("AWG toggle")["is on"]:
                                raw_card, controller = gui_open_awg()
                @toggle_state_and_enable(
                        "expo and roi fields", togCam, mItemLoadJson,
                        "awg panel",
                        "target array binary text input", menuConcurrency,
                        on_and_enable= False)
                def _dummy_toggle_acq_cb(sender, _ , user_data):
                    from camguihelper.core import (
                        _dummy_st_workerf_flagged_do_all,
                        _dummy_mt_producerf_polling_do_snag_rearrange_deposit,
                        _dummy_mp_producerf_polling_do_snag_rearrange_send,
                        )
                    state = user_data["is on"]
                    next_state = not state
                    flag = user_data["acq thread flag"]
                    if next_state:
                        str_json_saved = save_camgui_json_to_savetree()
                        str_json_displayed =  str_json_saved[:-5] + '已保存'
                        dpg.set_value(labelJson, str_json_displayed)
                    else:
                        str_json_displayed = dpg.get_value(labelJson)
                        json_num = int(str_json_displayed[2:][:-3])
                        str_json_displayed = 'CA' + str(json_num+1)
                        dpg.set_value(labelJson, str_json_displayed)
                    if dpg.get_value(mItemSingleThread):
                        if next_state:
                            t = threading.Thread(
                                target=_dummy_st_workerf_flagged_do_all, args=(flag, frame_deck))
                            user_data["thread1"] = t
                            flag.set()
                            t.start()
                        else:
                            t = user_data["thread1"]
                            flag.clear()
                            t.join()
                            user_data["thread1"] = None
                    elif dpg.get_value(mItemDualThreads):
                        if next_state:
                            t_producer = threading.Thread(target=_dummy_mt_producerf_polling_do_snag_rearrange_deposit, args=(flag,))
                            t_consumer = threading.Thread(target=consumerf_local_buffer, args=(frame_deck,))
                            user_data["thread1"] = t_producer
                            user_data["thread2"] = t_consumer
                            flag.set()
                            t_producer.start()
                            t_consumer.start()
                        else:
                            t_producer = user_data["thread1"]
                            t_consumer = user_data["thread2"]
                            flag.clear()
                            t_producer.join()
                            t_consumer.join()
                            user_data["thread1"] = None
                            user_data["thread2"] = None
                    else: # dual processes
                        if next_state:
                            conn_sig_main, conn_sig_child = multiprocessing.Pipe()
                            conn_data_main, conn_data_child = multiprocessing.Pipe()
                            conn_debug_main, conn_debug_child = multiprocessing.Pipe()
                            p_producer = multiprocessing.Process(
                                target=_dummy_mp_producerf_polling_do_snag_rearrange_send,
                                args=(conn_sig_child, 
                                      conn_data_child,
                                      conn_debug_child,
                                      _mp_dummy_remote_buffer)
                                )
                            t_passer = threading.Thread(
                                target=mp_passerf,
                                args= (conn_data_main,))
                            t_consumer = threading.Thread(
                                target=consumerf_local_buffer,
                                args=(frame_deck,))
                            user_data["signal connection"] = conn_sig_main # 投毒通道
                            user_data["process1"] = p_producer
                            user_data["thread1"] = t_passer
                            user_data["thread2"] = t_consumer
                            p_producer.start()
                            t_passer.start()
                            t_consumer.start()
                        else:
                            conn_sig_main = user_data["signal connection"] # 投毒通道
                            p_producer = user_data["process1"]
                            t_passer = user_data["thread1"]
                            t_consumer = user_data["thread2"]
                            conn_sig_main.send(None) # 投毒
                            conn_sig_main.close()
                            p_producer.join()
                            t_passer.join()
                            t_consumer.join()

                dpg.bind_item_font(togAcq, large_font)
                dpg.set_item_callback(togAcq, _toggle_acq_cb_)
                #==============================
                with dpg.child_window(height=122,no_scrollbar=True) as _cw:
                    with dpg.group(horizontal=True):
                        dpg.add_text("json:")
                        ttpkwargs = dict(delay=1, hide_on_activity= True)
                        with dpg.tooltip(dpg.last_item(), **ttpkwargs):
                            dpg.add_text("当前面板中所有的参数在触发采集开始时\n会被保存到这个文件夹")
                        labelJson = dpg.add_text("CA0")
                        dpg.bind_item_font(dpg.last_item(), large_font)
                    #===================================
                    with dpg.group(horizontal=True):
                        dpg.add_text("帧文件夹:")
                        with dpg.tooltip(dpg.last_item(), **ttpkwargs):
                            dpg.add_text("当前采集的所有帧文件(tiff)\n会被保存到这个文件夹")
                        _txtSes = dpg.add_text('0000')
                        dpg.bind_item_font(_txtSes, large_font)
                    _btnNewSes = dpg.add_button(label="新 session 帧文件夹")
                    def _twinkle():
                        dpg.configure_item(_txtSes, color = (255,0,255))
                        time.sleep(1)
                        dpg.configure_item(_txtSes, color = (255,255,255))
                    def _mk_newses_dir(*args):
                        try:
                            new_ses_str = mkdir_session_frames()
                            dpg.set_value(_txtSes, new_ses_str)
                            t = threading.Thread(target = _twinkle)
                            t.start()
                        except Exception:
                            push_exception("新 session 帧数据文件夹创建失败")
                            dpg.set_value(_txtSes, "错误")
                            dpg.configure_item(_txtSes, color = (255,0,0))
                    dpg.set_item_callback(_btnNewSes, _mk_newses_dir)
                with dpg.theme() as _thmSesBG:
                    with dpg.theme_component(dpg.mvChildWindow):
                        _ses_bg = (0,30,0)
                        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, _ses_bg)
                dpg.bind_item_theme(_cw, _thmSesBG)
                #====================================
                with dpg.group(tag = "expo and roi fields", enabled=False):
                    dpg.add_text("exposure time (ms):")
                    fldExposure = dpg.add_input_float(tag="exposure field",
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
                    _str = 'h start & h length:'
                    dpg.add_text(_str)
                    _indent = 20
                    fldsROIh = dpg.add_input_intx(tag = _str,size=2, indent= _indent,width=100, default_value=[1352, 240,0,0])
                    _str = 'v start & v length:'
                    dpg.add_text(_str)
                    fldsROIv = dpg.add_input_intx(tag = _str, size=2, indent = _indent ,width=dpg.get_item_width(fldsROIh), default_value=[948,240,0,0])
                    _str = 'h binning & v binning'
                    dpg.add_text(_str)
                    fldsBinning = dpg.add_input_intx(tag = _str, size=2, indent = _indent ,width=dpg.get_item_width(fldsROIh), default_value=[1,1,0,0])
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
                with dpg.theme() as _thmBlackBG:
                    with dpg.theme_component(dpg.mvChildWindow):
                        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (0,0,0))
                dpg.bind_item_theme(winLog, _thmBlackBG)
            with dpg.child_window(label = "awg panel"):
                with dpg.group(tag = "awg panel"):
                    togAwg = dpg.add_button(tag = "AWG toggle",
                        width=150, height=40, user_data={
                            "is on" : False, 
                            "off label" : "AWG 已关闭",
                            "on label" : "AWG 已开启",
                            })
                    dpg.bind_item_font(togAwg, large_font)
                    @toggle_state_and_enable()
                    def awg_toggle_cb(_,__,user_data):
                        global raw_card, controller
                        state = user_data["is on"]
                        next_state = not state
                        if next_state:
                            raw_card, controller = gui_open_awg() # raw_card is opened upon being returned by gui_open_awg()
                        else:
                            raw_card.close()
                            controller = None # controller always has to exist, since its the argument of the func start_acqloop that runs in the thread thread_acq
                    dpg.set_item_callback(togAwg, awg_toggle_cb)
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
        dpg.set_frame_callback(1,lambda: dpg.configure_item(winTgtArr, show=False)) # hide win on 1st frame, not during context creation, otherwise this hidden-by-default window's size won't be remembered by init file
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

    try: 
        _default_path = find_newest_daypath_in_save_tree(session_frames_root)
    except Exception:
        _default_path = session_frames_root
    # print(_default_path)
    with dpg.file_dialog( # file dialog 就是一个独立的 window, 因此在应该在 root 定义, 与其他 window 内的元素在形式上解耦
        label= '载入帧数据', directory_selector=False, 
        show=False, modal=True, default_path= _default_path,
        width=700, height=400) as fileDialog:
        # dpg.add_button(label="log", callback = _log)
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
            fname_dict = app_data["selections"]
            if "_select_all" in fname_dict:
                dpath = Path(app_data["current_path"])
                frame_list = [tifffile.imread(e) for e in dpath.iterdir() if e.suffix in [".tif", ".tiff"]]       
            else:
                frame_list = [tifffile.imread(e) for e in fname_dict.values()]          
            for e in frame_list:
                frame_deck.append(e)
                frame_deck.seslabel_deck.append("loaded")
            frame_deck.plot_frame_dwim()
        dpg.set_item_callback(fileDialog, _ok_cb_)
    try: 
        _default_path = find_newest_daypath_in_save_tree(camgui_params_root)
    except Exception:
        _default_path = camgui_params_root
    with dpg.file_dialog( # file dialog 就是一个独立的 window, 因此在应该在 root 定义, 与其他 window 内的元素在形式上解耦
        label= '载入 camgui json 文件', directory_selector=False,
        show=False, modal=True, default_path=  _default_path,
        width=700 ,height=400) as jsonDialog:
        dpg.add_file_extension("", color = (150,255,150,255)) # 让文件夹显示为绿色
        dpg.add_file_extension(".json")
        def _ok_cb_(_, app_data, __) -> None:
            dict_fnames : dict = app_data['selections']
            if len(dict_fnames)>1:
                push_log('只能选择一个 json 文件', is_error = True)
            else:
                fpath_json, = dict_fnames.values()
                with open(fpath_json, 'r') as f:
                    panel_params : Dict[Dict | str] = json.load(f)
                if panel_params['Camgui版本'] != camgui_ver:
                    push_log(
                        '注意! camgui 版本和创建 json 的 camgui 版本不一致', 
                        is_warning = True)
                for key, val in panel_params['并发方式'].items():
                    dpg.set_value(key, val)
                for key, val in panel_params['cam面板参数'].items():
                    dpg.set_value(key, val)
                    if dpg.get_item_user_data(togCam)['is on']:
                        do_set_cam_params_by_gui()
                for key, val in panel_params['awg面板参数'].items():
                    if key == 'awg is on':
                        past_awg_state = val
                    else:
                        dpg.set_value(key, val)
                    current_awg_state = dpg.get_item_user_data(togAwg)['is on']
                    if current_awg_state != past_awg_state:
                        awg_toggle_cb(togAwg, _ , dpg.get_item_user_data(togAwg))
                push_log(f'已载入 {fpath_json}', is_good = True)
        dpg.set_item_callback(jsonDialog, _ok_cb_)

    with dpg.window(label = "帧预览", tag=winFramePreview,
                    height=700, width=700
                    ):
        with dpg.menu_bar():
            with dpg.menu(label = "保存帧"):
                _mItemAutoSave = dpg.add_menu_item(label = "自动保存", tag = "autosave", check=True, default_value=True)
                def _theme_toggle(sender, *args):
                    if dpg.get_value(sender):
                        dpg.set_viewport_clear_color([0,0,0])
                        do_bind_my_default_global_theme()
                    else:
                        dpg.set_viewport_clear_color([50,0,0])
                        do_bind_my_global_nosave_theme()
                dpg.set_item_callback(_mItemAutoSave, _theme_toggle)
                fldSavePath = dpg.add_input_text(tag="save path input field",
                            hint="path to save tiff, e.g. C:\\Users\\username\\Desktop\\",
                            )
                dpg.add_menu_item(label = "保存内存中的当前帧到指定路径")
                dpg.set_item_callback(dpg.last_item(), lambda: frame_deck.save_cid_frame())
                #=============================
                dpg.add_menu_item(label = "保存内存中的所有帧到指定路径")
                dpg.set_item_callback(dpg.last_item(), lambda: frame_deck.save_deck())
                #================================
                dpg.add_menu_item(label = "清空内存中的帧")
                dpg.set_item_callback(dpg.last_item(),
                                        factory_cb_yn_modal_dialog(
                                            cb_on_confirm=frame_deck.clear, 
                                            dialog_text='确认要清空内存中的所有帧吗?'))
            #=========================
            dpg.add_menu_item(label = "载入帧", callback=lambda: dpg.show_item(fileDialog))
            with dpg.menu(label = "热图主题"):
                def factory_cb_bind_heatmap_cmap(cmap: int)-> Callable:
                    def cb_bind_heatmap_theme(sender, *args) ->None:
                        dpg.bind_colormap(frameColBar, cmap)
                        dpg.bind_colormap(framePlot, cmap)
                        for map in frame_deck.lst_dupe_maps:
                            tagPlotSlv = dpg.get_item_parent(map.yAxSlv)
                            dpg.bind_colormap(tagPlotSlv, cmap)
                        lst_other_menu_items: list = dpg.get_item_children(dpg.get_item_parent(sender))[1]
                        lst_other_menu_items.remove(sender)
                        dpg.set_value(sender, True)
                        for item in lst_other_menu_items:
                            dpg.set_value(item, False)
                        global myCmap
                        myCmap = cmap
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
        dpg.add_text(tag = "frame deck display", default_value= frame_deck.memory_report())
        dpg.bind_item_font(dpg.last_item(), bold_font)
        with dpg.group(label = "热图上下限, 帧翻页", horizontal=True) as grpPaging:
            _inputInt = dpg.add_drag_intx(tag = "color scale lims",label = "", size = 2, width=100, default_value=[0,65535,0,0], enabled=False, max_value=65535, min_value=0, clamped=True)
            with dpg.tooltip(_inputInt, **ttpkwargs): dpg.add_text("热图上下限, 最多 0-65535\n若未勾选'手动上下限', 则每次绘图自动用全帧最大/最小值作为上下限")
            def _set_color_scale(_, app_data, __):
                fmin, fmax, *_ = app_data
                # print(heatSeries)
                dpg.configure_item(frameColBar, min_scale = fmin, max_scale = fmax)
                for yAxSlv in frame_deck.get_all_maptags()[0]:
                    heatmapSlot = dpg.get_item_children(yAxSlv)[1]
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
            doubleplots_container_window_kwargs = dict(no_scrollbar = True, border=False)
            heatmap_pltkwargs = dict(no_mouse_pos=False, height=-1, width=-1, 
                                      equal_aspects=True,
                                       pos=(0,0), # double layer specific kwarg
                                       )
            heatmap_xyaxkwargs = dict(no_gridlines = True, no_tick_marks = True)
            heatmap_xkwargs = dict(label= "", opposite=True)
            heatmap_ykwargs = dict(label= "", invert=True)
            with dpg.theme() as thmTranspBGforMaster:
                """
                the transparent theme of master plot
                """
                with dpg.theme_component(dpg.mvPlot):
                    dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (0,0,0,0), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_FrameBg, (0,0,0,0), category=dpg.mvThemeCat_Plots)
            def factory_ihr_master_plot(xAxSlv, yAxSlv, xAxMstr, yAxMstr):
                """
                factory producing item handler registry to be bound to the master heatmap
                由于需要同步的 slave-master 的 x 轴和 y 轴需要 explicitly 指定 (dpg quirks),
                因此每一对 slave-master 的 ihr 都不一样, 需要一个 factory 来生成
                """
                with dpg.item_handler_registry() as ihrMaster:
                    dpg.add_item_visible_handler(
                        user_data = [xAxSlv, yAxSlv, xAxMstr, yAxMstr])
                    def sync_axes(_,__, user_data):
                        """
                        obtain master plot's axes range, using which we set the axes range of slave plot,
                        """
                        xax_slave, yax_slave, xax_master, yax_master = user_data
                        params_master = xmin_mst, xmax_mst, ymin_mst, ymax_mst = *dpg.get_axis_limits(xax_master), *dpg.get_axis_limits(yax_master)
                        params_slave = *dpg.get_axis_limits(xax_slave), *dpg.get_axis_limits(yax_slave)
                        if not params_master==params_slave:
                            dpg.set_axis_limits(xax_slave, xmin_mst, xmax_mst)
                            dpg.set_axis_limits(yax_slave, ymin_mst, ymax_mst)
                    dpg.set_item_callback(dpg.last_item(), sync_axes)
                    #=====================================
                    dpg.add_item_clicked_handler(dpg.mvMouseButton_Left)
                    def ctrl_add_dr(*args):
                        """
                        drag rect in dpg 2.0.0 is strange, 其行为很可能在后续 dpg 版本中得到修正
                        c.f. https://github.com/hoffstadt/DearPyGui/issues/2511
                        - drag rect 属于 plot, 不属于 axes
                        - drag rect 不能绑定任何 item handler registry
                        - drag rect 没有 app_data (None)
                        - drag rect 的当前四角位置可以通过 dpg.get_value(dragRect) 获取,
                          其实时四角位置可以通过 drag rect 的 callback 连续获取(人工拖动时才连续触发)
                        """
                        if dpg.is_key_down(dpg.mvKey_LControl):
                            x, y = dpg.get_plot_mouse_pos()
                            frame_deck.add_dr_to_loc(x, y)
                    dpg.set_item_callback(dpg.last_item(), ctrl_add_dr)
                    #=====================================
                    dpg.add_item_clicked_handler()
                    def alt_remove_dr(*args):
                        if dpg.is_key_down(dpg.mvKey_LAlt):
                            x, y = dpg.get_plot_mouse_pos()
                            frame_deck.remove_dr_from_loc(x,y)
                    dpg.set_item_callback(dpg.last_item(), alt_remove_dr)
                return ihrMaster
            gen_dupemap_label = cycle(range(100)) # 假设不可能同时打开 100 个窗口, 因此新开的窗口 label 可以是 0-99 的循环, 足以保证 label uniqueness
            with dpg.handler_registry():
                dpg.add_key_press_handler(
                    dpg.mvKey_F11, 
                    callback = factory_cb_yn_modal_dialog(
                        cb_on_confirm= frame_deck.clear_dr,
                        dialog_text='确认要清除所有的直方图选区吗?'))
                #========================================
                dpg.add_key_press_handler(dpg.mvKey_F12, 
                                          user_data=[] # list for holding annotation item tags
                                          )
                def _show_hide_grp_id(sender, __, user_data):
                    if user_data:
                        while user_data:
                            dpg.delete_item(user_data.pop())
                    else:
                        _,_,lst_pltMstr = frame_deck.get_all_maptags()
                        for grp_id, ddict in frame_deck.dict_dr.items():
                            if ddict is not None:
                                xminf, yminf, xmaxf, ymaxf = ddict['fence']
                                xmeanf, ymeanf = (xminf+xmaxf)/2, (yminf+ymaxf)/2
                                for thisPlot in lst_pltMstr:
                                    annoTag = dpg.add_plot_annotation(
                                        parent=thisPlot,
                                        label= str(grp_id),
                                        default_value=(xmeanf, ymeanf),
                                        color = [255,255,0])
                                    user_data.append(annoTag)
                    dpg.set_item_user_data(sender, user_data)
                dpg.set_item_callback(dpg.last_item(), _show_hide_grp_id)
                #================================
                _kph = dpg.add_key_press_handler(dpg.mvKey_F9)
                def make_dr_arr(*args):
                    if len(frame_deck.dq2)<2: # 如果(单张热图上)的直方图选区少于两个, 则不触发选区阵列选取
                        return
                    
                    with dpg.window(
                        label = '添加阵列选区 - 1d', modal = True, pos = get_viewport_centerpos(),
                        on_close = lambda sender: dpg.delete_item(sender)) as queryWin1:
                        # print('in window container')
                        dpg.add_text('在最近创建的两个选区之间(含), 你要创建多少选区\n(新创建的选区面积和当前最新的选区一致)')
                        # print('past text')
                        inputInt1D = dpg.add_input_int(default_value= 10, min_value=2, min_clamped=True)
                        dpg.add_spacer(height=10)
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width = 30)
                            yesBtn1 = dpg.add_button(label = '好')
                            def make_1d_dr_arr_and_query_for_2d(*args):
                                (grp1, uuid1), (grp2, uuid2) = frame_deck.dq2 # 2 is newer, 1 older
                                if not (frame_deck.series_uuid_exists(uuid1) and frame_deck.series_uuid_exists(uuid2)):
                                    """
                                    如果用户最新创建的两个选区有删除后重新创建的, 那么会出错, 我懒得严格判定这种情况下的真正的最新的两个选区了, 直接提示让用户全选
                                    """
                                    push_log('请重新创建两个选区, 创建后不要删除, 再执行 1d 选区阵列创建', is_warning = True)
                                    dpg.delete_item(queryWin1)
                                    return
                                def get_dr_pos(grp_id: int, series_uuid: str)->Tuple[float]:
                                    df = frame_deck.dict_dr[grp_id]['grp dr df']
                                    drTagRep = df[series_uuid].iloc[0]
                                    return dpg.get_value(drTagRep) # x1, y1, x2, y2
                                x1dr1, y1dr1, x2dr1, y2dr1 = get_dr_pos(grp1, uuid1)
                                x1dr2, y1dr2, x2dr2, y2dr2 = get_dr_pos(grp2, uuid2)
                                xmeandr1, ymeandr1 = (x1dr1+x2dr1)/2, (y1dr1+y2dr1)/2
                                xmeandr2, ymeandr2 = (x1dr2+x2dr2)/2, (y1dr2+y2dr2)/2
                                sidex_dr2, sidey_dr2 = abs(x1dr2-x2dr2), abs(y1dr2-y2dr2)
                                n_dr1d = dpg.get_value(inputInt1D)
                                lst_xymeans_todo_for_1darr = [
                                    (x,y) for (x,y) in
                                    zip(np.linspace(xmeandr1, xmeandr2, n_dr1d), 
                                        np.linspace(ymeandr1, ymeandr2, n_dr1d))]
                                lst_xymeans_todo_for_1darr = lst_xymeans_todo_for_1darr[1:]
                                frame_deck.expunge_dr_series(grp2, uuid2)
                                for xcen, ycen in lst_xymeans_todo_for_1darr:
                                    _, uuid_1dlast = frame_deck.add_dr_to_loc(xcen, ycen, sidex=sidex_dr2, sidey=sidey_dr2)
                                dpg.delete_item(queryWin1)
                                with dpg.window(
                                    label = '添加阵列选取 - 2d',
                                    pos = (0,0), #np.array(get_viewport_centerpos())/3,
                                    on_close = lambda sender: dpg.delete_item(sender)
                                    ) as queryWin2:
                                    dpg.add_text('1d 选区组创建成功, 如果只需要 1d 选区组, 请直接关闭本窗口.\n\n\如果需要 2d 选区阵列, 请再添加一个选区, 过该选区中心与已创建的 1d 选区组相平行的线会界定待创建的 2d 选区阵列的另一条边. 在这两条边之间, 你希望存在几排 1d 选区组(含已经创建 1d 选区组)? 在下方设置',
                                                 wrap=300)
                                    inputInt2D = dpg.add_input_int(default_value= 10, min_value=2, min_clamped=True)
                                    dpg.add_spacer(height=10)
                                    with dpg.group(horizontal=True):
                                        dpg.add_spacer(width=30)
                                        yesBtn2= dpg.add_button(label='好')
                                        def make_2d_dr_arr(*args):
                                            grp3, uuid3 = frame_deck.dq2[-1]
                                            if uuid3==uuid_1dlast:
                                                push_log('请添加 2d 选区阵列所需的新选区', is_warning = True)
                                                return
                                            x1dr3, y1dr3, x2dr3, y2dr3 = get_dr_pos(grp3, uuid3)
                                            frame_deck.expunge_dr_series(grp3, uuid3)
                                            xmeandr3, ymeandr3 = (x1dr3+x2dr3)/2, (y1dr3+y2dr3)/2
                                            def rz(theta : float)-> np.ndarray:
                                                """
                                                before rotation:
                                                        *2
                                                *1   
                                                    
                                                
                                                *3

                                                after rotation (where we get x1r, y1r, etc.):
                                                     *1------*2

                                                *3--------------

                                                do meshgrid (where we get xx and yy):
                                                    *1------*2
                                                    + + + + +
                                                    + + + + +
                                                *3  + + + + +

                                                `+` points are the new points we want, 
                                                now rotate them back to get their desirable coordinates
                                                """
                                                return np.array(
                                                    [[np.cos(theta), -np.sin(theta)],
                                                     [np.sin(theta), np.cos(theta)],])
                                            theta = np.arctan2(ymeandr2-ymeandr1, xmeandr2-xmeandr1)
                                            x1r, y1r= rz(-theta)@(xmeandr1, ymeandr1) # point 1 rotated
                                            x2r, y2r= rz(-theta)@(xmeandr2, ymeandr2) # point 2 rotated
                                            x3r, y3r= rz(-theta)@(xmeandr3, ymeandr3) # point 3 rotated
                                            n_dr2d = dpg.get_value(inputInt2D)
                                            xx, yy = np.meshgrid(np.linspace(x1r, x2r, n_dr1d),
                                                                 np.linspace(y1r, y3r, n_dr2d),)
                                            xyarr = [(x,y) for x,y in zip(xx.flatten(), yy.flatten())] # .reshape((n_dr2d, -1))
                                            xyarr = xyarr[n_dr1d:] # the 1d arr is already done, do not re-create it
                                            xyarr_rot_back = [rz(theta)@p for p in xyarr]
                                            for xcen, ycen in xyarr_rot_back:
                                                frame_deck.add_dr_to_loc(xcen, ycen, sidex=sidex_dr2, sidey=sidey_dr2)
                                            dpg.delete_item(queryWin2)
                                        dpg.set_item_callback(yesBtn2, make_2d_dr_arr)

                            dpg.set_item_callback(yesBtn1, make_1d_dr_arr_and_query_for_2d)
                dpg.set_item_callback(_kph, make_dr_arr)
            def _dupe_heatmap():
                dupe_map = DupeMap(
                    pltSlv = dpg.generate_uuid(),
                    pltMstr = dpg.generate_uuid(),
                    yAxSlv = dpg.generate_uuid(),
                    yAxMstr = dpg.generate_uuid(),
                    inputInt = dpg.generate_uuid(),
                    radioBtn = dpg.generate_uuid(),
                    cBox = dpg.generate_uuid())
                def _on_close(sender, *args):
                    """
                    window 的 on close callback 貌似不同于普通 callback, 只能在创建 window 时设置, 
                    因此这里将这个 callback 定义在先
                    """
                    frame_deck.lst_dupe_maps.remove(dupe_map)
                    dpg.delete_item(sender)
                    for ddict in frame_deck.dict_dr.values():
                        if ddict is not None:
                            ddict['grp dr df'].drop(
                                dupe_map.pltMstr,
                                inplace=True)
                with dpg.window(width=300, height=300, on_close=_on_close,
                                label = f"#{next(gen_dupemap_label)}"):
                    frame_deck.lst_dupe_maps.append(dupe_map)
                    with dpg.group(horizontal=True) as _grp:
                        #==============================
                        dpg.add_input_int(width=100, tag=dupe_map.inputInt, max_value=0, max_clamped=True, 
                                        #   callback=_log
                                        )
                        def _cb_input_int(*args):
                            frame_deck._update_dupe_map(dupe_map)
                        dpg.set_item_callback(dupe_map.inputInt, _cb_input_int)
                        #===============================
                        dpg.add_radio_button(('倒数帧', '正数帧'), tag=dupe_map.radioBtn,
                                            default_value = '倒数帧', horizontal=True,)
                        def _cb_radio(_, app_data, __):
                            """
                            这个 radio button 的 callback 必须放在 enclosing 的 _dupe_heatmap callback 定义中,
                            因为它需要操纵的 item 是 enclosing callback 创造的对象, 需要利用 enclosing scope 中的变量 inputInt
                            """
                            input_id = dpg.get_value(dupe_map.inputInt)
                            empty_deck = True if not frame_deck.cid else False
                            if empty_deck:
                                dpg.set_value(dupe_map.inputInt, 0)
                            else:
                                if app_data == '倒数帧': # convert forward id to backward id
                                    converted_id = input_id - len(frame_deck) + 1
                                else: # convert backward id to forward id
                                    converted_id = input_id + len(frame_deck) - 1 
                                dpg.set_value(dupe_map.inputInt, converted_id)
                            if app_data == '倒数帧': # unlim low bound, lim high bound to 0
                                dpg.configure_item(dupe_map.inputInt, min_clamped = False)
                                dpg.configure_item(dupe_map.inputInt, max_value = 0, max_clamped = True)
                            else: # unlim high bound, lim low bound to 0
                                dpg.configure_item(dupe_map.inputInt, max_clamped = False)
                                dpg.configure_item(dupe_map.inputInt, min_value = 0, min_clamped = True)
                        dpg.set_item_callback(dupe_map.radioBtn, _cb_radio)
                    with dpg.child_window(**doubleplots_container_window_kwargs):
                        def apply_common_plt_children_setups_slv_mstr(yAx: int):
                            xax = dpg.add_plot_axis(dpg.mvXAxis, **heatmap_xkwargs, **heatmap_xyaxkwargs)
                            dpg.add_plot_axis(dpg.mvYAxis, tag=yAx, **heatmap_ykwargs, **heatmap_xyaxkwargs)
                            xaxlims_orig, yaxlims_orig = dpg.get_axis_limits("frame xax"), dpg.get_axis_limits("frame yax")
                            dpg.set_axis_limits(xax, *xaxlims_orig)
                            dpg.set_axis_limits(yAx, *yaxlims_orig)
                            dpg.split_frame()
                            dpg.set_axis_limits_auto(xax)
                            dpg.set_axis_limits_auto(yAx)
                            return xax
                        lst_axes = []
                        with dpg.plot(tag = dupe_map.pltSlv, **heatmap_pltkwargs): # slave plot
                            dpg.bind_colormap(dpg.last_item(), myCmap)
                            xAxSlv = apply_common_plt_children_setups_slv_mstr(dupe_map.yAxSlv)
                            lst_axes.append(xAxSlv)
                            lst_axes.append(dupe_map.yAxSlv)
                        with dpg.plot(tag = dupe_map.pltMstr, **heatmap_pltkwargs): # master plot
                            xAxMstr = apply_common_plt_children_setups_slv_mstr(dupe_map.yAxMstr)
                            lst_axes.append(xAxMstr)
                            lst_axes.append(dupe_map.yAxMstr)
                        dpg.bind_item_theme(dupe_map.pltMstr, thmTranspBGforMaster)
                        dpg.bind_item_handler_registry(
                            dupe_map.pltMstr, factory_ihr_master_plot(*lst_axes))
                        #======================
                        dpg.add_checkbox(pos = (0,0), tag = dupe_map.cBox) # 要画在 plot 上, 所以在 plot 后添加
                        @toggle_checkbox_and_disable(_grp)
                        def _toggle_id_and_avg_map_(sender, *args):
                            frame_deck._update_dupe_map(dupe_map)
                        dpg.set_item_callback(dupe_map.cBox, _toggle_id_and_avg_map_)
                        with dpg.tooltip(dupe_map.cBox, **ttpkwargs):
                            dpg.add_text("切换单帧/平均帧")
                #=== 在创建好 dupe map 后, 载入热图和 dr
                frame_deck.plot_cid_frame(dupe_map.yAxSlv, dupe_map.yAxMstr)
                # 下面的部分为 frame_deck.dict_dr['grp dr df'] 添加行, 而函数 frame_deck.add_dr_to_all 添加列
                # 由于所有 maps 中的 dr 都需要同步, 因此这两种添加方式是唯二的两种添加方式, 不可能存在单独添加 cell 的添加方式
                # 换句话说, 我可能设想用某个 add_dr_to_one_map 一个一个将 dr 添加到一个 map 上,
                # 然后将其 wrap 为一个 add_dr_to_all_maps 函数, 用于处理多添加的情况, 但是这种逻辑破坏了我在 add_dr_to_all 中的同步逻辑
                # 并且不见得比添加行/列的逻辑更优越
                for grp_id, ddict in frame_deck.dict_dr.items():
                    if ddict is not None:
                        df = ddict['grp dr df']
                        dr_row = df.iloc[0,:] # 取主热图上所有的 dr
                        lst_dr_in_this_dupemap = [
                            dpg.add_drag_rect(
                                parent = dupe_map.pltMstr,
                                default_value=dpg.get_value(drTag),
                                callback = frame_deck.sync_rects_and_update_fence
                                )
                            for drTag in dr_row]
                        for this_drTag, this_uuid in zip(lst_dr_in_this_dupemap, df.columns):
                            dpg.set_item_user_data(this_drTag, (grp_id, this_uuid))
                            dpg.configure_item(this_drTag, color = frame_deck.get_dr_color_in_group(grp_id))
                        df.loc[dupe_map.pltMstr] = lst_dr_in_this_dupemap
                        ddict['grp dr df'] = df

            dpg.set_item_callback(cidIndcator, _dupe_heatmap)
            #==========================================
            rightArr = dpg.add_button(tag = "plot next frame", label=">", arrow=True, direction=dpg.mvDir_Right)
            def _right_arrow_cb_(*cbargs):
                if frame_deck and (frame_deck.cid<len(frame_deck)-1):
                    frame_deck.cid += 1
                    frame_deck.plot_cid_frame()
                    dpg.set_item_label(cidIndcator, f"{frame_deck.cid}")
            dpg.set_item_callback(rightArr, _right_arrow_cb_)
        with dpg.group(horizontal=True) as GrpMainFramePlot:
            frameColBar = dpg.add_colormap_scale(tag = "frame colorbar", min_scale=0, max_scale=500, 
                                height=-1
                                )
            dpg.bind_colormap(dpg.last_item(), myCmap)
            with dpg.child_window(**doubleplots_container_window_kwargs): # 这个 child window 的唯一作用是让 double layer 的 plots 能够用相同的 pos 参数
                #==slave plot=============================
                with dpg.plot(tag="frame plot",
                            # query=True, query_color=(255,0,0), max_query_rects=1, min_query_rects=0,
                            **heatmap_pltkwargs) as framePlot:
                    dpg.bind_colormap(dpg.last_item(), myCmap)
                    
                    dpg.add_plot_axis(dpg.mvXAxis, tag = "frame xax", **heatmap_xkwargs, **heatmap_xyaxkwargs)
                    frameYax = dpg.add_plot_axis(dpg.mvYAxis, tag= "frame yax", **heatmap_ykwargs, **heatmap_xyaxkwargs)
                #==master plot=============================
                with dpg.plot(**heatmap_pltkwargs) as _pltMstr:
                    rectsXax = dpg.add_plot_axis(dpg.mvXAxis, **heatmap_xkwargs, **heatmap_xyaxkwargs)
                    rectsYax = dpg.add_plot_axis(dpg.mvYAxis, tag = 'rects yax', **heatmap_ykwargs, **heatmap_xyaxkwargs)
                dpg.bind_item_theme(_pltMstr, thmTranspBGforMaster)
                dpg.bind_item_handler_registry(
                    _pltMstr, factory_ihr_master_plot('frame xax', 'frame yax', rectsXax, rectsYax))
                for ax in ["frame xax", "frame yax", rectsXax, rectsYax]:
                    dpg.set_axis_limits(ax, 0, 240)
                    # dpg.split_frame() # waits forever because frames are not rolling in the context creation stage
                def _do_loosen_initial_lims():
                    for ax in ["frame xax", "frame yax", rectsXax, rectsYax]:
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
                dpg.set_item_callback(framePlot, callback=_update_hist_on_query_)
                #===本 checkbox 需要画在 plot 上面, 因此在 plot 后添加
                dpg.add_checkbox(tag="toggle 积分/单张 map", pos = (0, 0))
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
        with dpg.group(label = '四个箭头按钮, 单像素整体移动所有直方图选区', horizontal=True):
                dpg.add_button(arrow=True, direction=dpg.mvDir_Left)
                dpg.add_button(arrow=True, direction=dpg.mvDir_Right)
                dpg.add_button(arrow=True, direction=dpg.mvDir_Up)
                dpg.add_button(arrow=True, direction=dpg.mvDir_Down)
                dpg.add_text('单像素移动所有直方图选区')
    with dpg.item_handler_registry() as ihrWinFramePreview:
        def show_bottom_arrows(*args):
            width, height = dpg.get_item_rect_size(winFramePreview)
            reserved_height = 165
            dpg.configure_item(GrpMainFramePlot, height=height - reserved_height)
        dpg.add_item_resize_handler(callback = show_bottom_arrows)
    dpg.bind_item_handler_registry(winFramePreview, ihrWinFramePreview)
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
    with dpg.window(label = '阵列直方图', width = 200, height=300):
        ...
    if dummy_acq: #True is dummy acquisition
        dpg.set_item_callback(togCam,_dummy_cam_toggle_cb_)
        dpg.set_item_callback(togAcq, _dummy_toggle_acq_cb)
        cam = None # probably needed for dummy acquisition, the same reason as needing controller = None
        dpg.add_checkbox(tag = "假触发", label = "假触发", parent=grpPaging, callback=_log)
        from camguihelper.core import _workerf_dummy_remote_buffer_feeder, _mp_workerf_dummy_remote_buffer_feeder
        t_mt_remote_buffer_feeder = threading.Thread(target = _workerf_dummy_remote_buffer_feeder)
        t_mt_remote_buffer_feeder.start()
        t_mp_remote_buffer_feeder = threading.Thread(target = _mp_workerf_dummy_remote_buffer_feeder, args=(_mp_dummy_remote_buffer,))
        t_mp_remote_buffer_feeder.start()
    # dpg.show_style_editor()
    # dpg.show_item_registry()
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
