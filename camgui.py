#%%
import dearpygui.dearpygui as dpg
from pylablib.devices import DCAM
import threading
import time
import math
import tifffile
from camguihelper import gui_open_awg, FrameStack, start_flag_watching_acq
from camguihelper.core import _log, _update_hist
from camguihelper.dpghelper import (
    do_bind_my_global_theme,
    do_initialize_chinese_fonts,
    do_extend_add_button,
    toggle_checkbox_and_disable,
    factory_cb_yn_modal_dialog)
controller = None # controller always has to exist, since its the argument of the func start_acqloop that runs in the thread thread_acq
from tiff_imports import flist
frame_stack = FrameStack() # the normal empty frame_stack creation
frame_stack = FrameStack(flist) # the override to import fake data

dpg.create_context()
do_bind_my_global_theme()
_, bold_font, large_font = do_initialize_chinese_fonts()
toggle_theming_and_enable = do_extend_add_button()

dpg.create_viewport(title='camera', 
                    width=1260, height=1020, x_pos=0, y_pos=0,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

with dpg.window(tag="win1", pos=(0,0)):
    with dpg.group(horizontal=True):
        with dpg.group():
            with dpg.group(horizontal=True, height=720):
                with dpg.child_window(width=210):
                    _wid, _hi = 175, 40
                    togCam = dpg.add_button(
                        width=_wid, height=_hi, user_data={
                            "is on" : False, 
                            "off label" : "相机已关闭",
                            "on label" : "相机已开启",
                            })
                    dpg.bind_item_font(togCam, large_font)
                    @toggle_theming_and_enable("expo and roi fields", 
                                            "acquisition toggle")
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
                            cam.close(); print("=====cam closed")
                            # cam = None # I actually want to retain a closed cam object after toggling off the cam, for cam checks that might be useful
                    @toggle_theming_and_enable("expo and roi fields", "acquisition toggle")
                    def _dummy_cam_toggle_cb_(_, __, user_data):
                        state = user_data["is on"]
                        next_state = not state # state after toggle
                        if next_state:
                            time.sleep(0.5)
                        else:
                            time.sleep(0.5)
                    _cam_toggle_cb_ = _dummy_cam_toggle_cb_
                    dpg.set_item_callback(togCam,_cam_toggle_cb_)

                    togAcq = dpg.add_button(tag="acquisition toggle", enabled=False,
                        width=_wid, height=_hi, user_data={
                            "is on" : False, 
                            "off label" : "触发采集已停止",
                            "on label" : "触发采集进行中",
                            "acq thread flag": threading.Event(),
                            "acq thread": None,
                            })
                    @toggle_theming_and_enable(
                            "expo and roi fields", togCam, "awg panel",
                            "target array window", on_and_enable= False)
                    def _toggle_acq_cb_(sender, _, user_data):
                        state = user_data["is on"]
                        next_state = not state
                        flag = user_data["acq thread flag"]
                        if next_state:
                            thread_watching_a_flag = threading.Thread(target=start_flag_watching_acq, args=(cam, flag, frame_stack, controller))
                            user_data["acq thread"] = thread_watching_a_flag
                            flag.set()
                            thread_watching_a_flag.start()
                        else:
                            thread_watching_a_flag = user_data["acq thread"]
                            flag.clear()
                            thread_watching_a_flag.join()
                            user_data["acq thread"] = None
                            cam.stop_acquisition()
                            cam.set_trigger_mode("int")
                            print("acq stopped")
                        dpg.set_item_user_data(sender, user_data)
                    dpg.bind_item_font(togAcq, large_font)
                    dpg.set_item_callback(togAcq, _toggle_acq_cb_)
                    dpg.add_separator()
                    with dpg.group(tag = "expo and roi fields",horizontal=False, enabled=False) as groupExpoRoi:
                        dpg.add_text("exposure time (ms):")
                        fldExposure = dpg.add_input_float(
                            width = 120, step=0, format="%.4f",
                            default_value= 100)
                        def _set_cam_exposure(_, app_data, __): # the app_data in this case is the same as dpg.get_value(fldExposure)
                            time_in_ms, cam = app_data, dpg.get_item_user_data(togCam)["camera object"]
                            cam.set_exposure(time_in_ms*1e-3)
                        dpg.set_item_callback(fldExposure, _set_cam_exposure)
                        with dpg.item_handler_registry() as _ihrUpdateFldExposureOnLeave:
                            def _cam_updates_fldExposure(*cbargs):
                                cam_internal_expo_in_ms = cam.cav["exposure_time"] * 1e3
                                dpg.set_value(fldExposure, cam_internal_expo_in_ms)
                            dpg.add_item_deactivated_after_edit_handler(callback= _cam_updates_fldExposure)
                        dpg.bind_item_handler_registry(fldExposure, _ihrUpdateFldExposureOnLeave)
                        dpg.add_spacer(height=10)
                        dpg.add_separator(label="ROI (max h 4096, v 2304)")
                        dpg.add_text("h start & h length:")
                        _indent = 20
                        fldsROIh = dpg.add_input_intx(size=2, indent= _indent,width=100, default_value=[1352, 240,0,0])
                        dpg.add_text("v start & v length:")
                        fldsROIv = dpg.add_input_intx(size=2, indent = _indent ,width=dpg.get_item_width(fldsROIh), default_value=[948,240,0,0])
                        dpg.add_text("h binning & v binning")
                        fldsBinning = dpg.add_input_intx(size=2, indent = _indent ,width=dpg.get_item_width(fldsROIh), default_value=[1,1,0,0])
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
                
                with dpg.child_window(width=760, label="012"):
                    with dpg.group(horizontal=True):
                        fldSavePath = dpg.add_input_text(tag="save path input field ",
                            hint="path to save tiff, e.g. C:\\Users\\username\\Desktop\\", width=600)
                        btnLoad = dpg.add_button(label="载入帧", callback=lambda: dpg.show_item("file dialog"))
                        def _cb_(_, app_data, __):
                            global frame_stack
                            fname_dict = app_data["selections"]
                            if fname_dict:
                                frame_list = [tifffile.imread(e) for e in fname_dict.values()]
                                frame_stack = FrameStack(frame_list)
                                frame_stack._update()
                                    
                        with dpg.file_dialog(directory_selector=False, show=False, 
                                            callback=_cb_, tag="file dialog",
                                            width=700 ,height=400):
                            dpg.add_file_extension(".tif")
                            dpg.add_file_extension(".tiff")
                    with dpg.group(horizontal=True):
                        frameStackCnt = dpg.add_text(tag = "frame stack count display", default_value= "0 frames in stack")
                        btnSaveAll = dpg.add_button(label="保存所有帧")
                        def _save_all_frames_(*cbargs):
                            saved_p = frame_stack.save_stack()
                            if saved_p:
                                frame_stack.clear()
                                msg = "0 frames in stack"
                            else:
                                msg = "NOT Saved!"
                            dpg.set_value(frameStackCnt, msg)
                        dpg.set_item_callback(btnSaveAll, _save_all_frames_)
                        
                        _btnClearStack = dpg.add_button(label="清空所有帧")
                        def _on_confirm():
                            frame_stack.clear()
                            dpg.set_value(frameStackCnt, "0 frames in stack")
                            dpg.delete_item("confirmation_modal")  # Close the modal after confirming
                        dpg.set_item_callback(_btnClearStack,
                                              factory_cb_yn_modal_dialog(cb_on_confirm=_on_confirm, dialog_text="确认要清空内存中的所有帧吗?"))
                        _btnSaveCurrent = dpg.add_button(label="保存当前帧")
                        def _save_current_frame_(*cbargs):
                            saved_p = frame_stack.save_cid_frame()
                            if saved_p:
                                dpg.set_value(frameStackCnt, "Saved!")
                            else:
                                dpg.set_value(frameStackCnt, "NOT Saved!")
                        dpg.set_item_callback(_btnSaveCurrent, _save_current_frame_)
                        dpg.bind_item_font(frameStackCnt, bold_font)
                    dpg.add_separator()
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag = "manual scale checkbox", label = "自定义热图上下限")
                        dpg.add_input_intx(tag = "color scale lims",label = "热图上下限 (最多 0-65535)", size = 2, width=120, default_value=[0,65535,0,0])
                        dpg.add_spacer(width=10)
                        with dpg.group(horizontal=True):
                            def _left_arrow_cb_(*cbargs):
                                if frame_stack.cid:
                                    frame_stack.cid -= 1
                                    frame_stack.plot_cid_frame()
                            def _right_arrow_cb_(*cbargs):
                                if frame_stack and (frame_stack.cid<len(frame_stack)-1):
                                    frame_stack.cid += 1
                                    frame_stack.plot_cid_frame()
                            leftArr = dpg.add_button(tag = "plot previous frame", label="<", arrow=True)
                            rightArr = dpg.add_button(tag = "plot next frame", label=">", arrow=True, direction=dpg.mvDir_Right)
                            dpg.set_item_callback(leftArr, _left_arrow_cb_)
                            dpg.set_item_callback(rightArr, _right_arrow_cb_)
                        dpg.add_spacer(width=10)
                        cboxTogAvgMap = dpg.add_checkbox(label="stack 平均图",tag="toggle 积分/单张 map")
                        @toggle_checkbox_and_disable(leftArr, rightArr)
                        def _toggle_cid_and_avg_map_(_, app_data,__):
                            if app_data:
                                frame_stack.plot_avg_frame()
                            else:
                                frame_stack.plot_cid_frame()
                        dpg.set_item_callback(cboxTogAvgMap, _toggle_cid_and_avg_map_)
                    with dpg.group(horizontal=True):
                        _cmap = dpg.mvPlotColormap_Viridis
                        dpg.add_colormap_scale(tag = "frame colorbar", min_scale=0,max_scale=65535, height=400)
                        dpg.bind_colormap(dpg.last_item(), _cmap)
                        _side = 600
                        with dpg.plot(tag="frame plot", no_mouse_pos=False, height=_side, width=_side,
                                    query=True, query_color=(255,0,0), max_query_rects=1, min_query_rects=0):
                            dpg.bind_colormap(dpg.last_item(), _cmap)
                            _xyaxeskwargs = dict(no_gridlines = True, no_tick_marks = True)
                            dpg.add_plot_axis(dpg.mvXAxis, tag = "frame xax", label= "h", opposite=True, **_xyaxeskwargs)
                            dpg.add_plot_axis(dpg.mvYAxis, tag= "frame yax", label= "v", invert=True, **_xyaxeskwargs)
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
                                        dpg.set_item_user_data("frame plot", hLhRvLvR)
                                        if hLlim <= hRlim and vLlim <=vRlim: # make sure at least one pixel's geo center falls within the query rect
                                            _update_hist(hLhRvLvR, frame_stack)
                                else: # this is only needed for the current query rect solution for hist udpates. actions from other items cannot check app_data of this item directly (usually dpg.get_value(item) can check the app_data of an item, but not for this very special query rect coordinates app_data belonging to the heatmap plot!), so they check the user_data of this item. since I mean to stop any histogram updating when no query rect is present, then this no-rect info is given by user_data = None of the heatmap plot.
                                    dpg.set_item_user_data(sender, None)
                            dpg.set_item_callback("frame plot",callback=_update_hist_on_query_)
            with dpg.child_window(width = 928): # 为了让下面的 hist binning field 可以自然地从一个 window 的左上角开始选取 h，v 坐标，所以这里设置一个 child window
                with dpg.plot(tag="hist plot", label = "hist", height=-1, width=-1, no_mouse_pos=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label = "converted counts ((<frame pixel counts>-200)*0.1/0.9)")
                    dpg.add_plot_axis(dpg.mvYAxis, label = "frequency", tag = "hist plot yax")
                dpg.add_input_int(pos=(80,10), tag = "hist binning input",label="hist binning", width=80,
                                min_value=1, default_value=1, min_clamped=True)
        
        with dpg.child_window(tag = "awg panel"):
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
                    raw_card.close()
                    controller = None # controller always has to exist, since its the argument of the func start_acqloop that runs in the thread thread_acq
            dpg.set_item_callback(togAwg, _awg_toggle_cb_)
            dpg.add_separator()
            _width=100
            _spcheight=10
            dpg.add_input_intx(label= "x1 y1", tag= "x1 y1", size=2, width=_width, default_value = [36,23,0,0])
            dpg.add_input_intx(label= "x2 y2", tag= "x2 y2", size=2, width=_width, default_value = [124,25,0,0])
            dpg.add_input_intx(label= "x3 y3", tag= "x3 y3", size=2, width=_width, default_value = [34,112,0,0])
            dpg.add_input_intx(label= "nx ny", tag= "nx ny", size=2, width=_width, default_value = [16,16,0,0])
            dpg.add_input_intx(label= "x0 y0", tag= "x0 y0", size=2, width=_width, default_value = [34,21,0,0])
            dpg.add_input_intx(label= "rec_x rec_y", tag= "rec_x rec_y", size=2, width=_width, default_value=[4,4,0,0])
            dpg.add_input_int(label="count_threshold",tag="count_threshold",step=0, width=_width/2, default_value=30)
            dpg.add_input_int(label="n_packed",tag="n_packed",step=0, width=_width/2, default_value=3)
            dpg.add_spacer(height=_spcheight)
            dpg.add_text("start_frequency_on_row(col)")
            dpg.add_input_floatx(tag = "start_frequency_on_row(col)", size=2, width=_width*1.2, default_value=[90.8,111.4,0,0], label="MHz")
            dpg.add_text("end_frequency_on_row(col)")
            dpg.add_input_floatx(tag = "end_frequency_on_row(col)", size=2, width=_width*1.2, default_value=[111.3,90.8,0,0], label= "MHz")
            dpg.add_text("start_site_on_row(col)")
            dpg.add_input_intx(tag = "start_site_on_row(col)", size=2, width=_width, default_value=[0,0,0,0])
            dpg.add_text("end_site_on_row(col)")
            dpg.add_input_intx(tag = "end_site_on_row(col)", size=2, width=_width, default_value=[15,15,0,0])
            dpg.add_spacer(height=_spcheight)
            dpg.add_input_int(label="num_segments", tag="num_segments",step=0, width=_width/2, default_value=16)
            dpg.add_input_float(label="power_ramp_time (ms)", tag="power_ramp_time (ms)",step=0, width=_width/2, default_value=4)
            dpg.add_input_float(label="move_time (ms)", tag="move_time (ms)", step=0, width=_width/2, default_value=2)
            dpg.add_spacer(height=_spcheight)
            dpg.add_text("percentage_total_power_for_list")
            dpg.add_input_float(tag = "percentage_total_power_for_list", step=0, width=_width/2, default_value=0.5)
            dpg.add_input_text(label = "ramp_type", tag = "ramp_type", width=_width, default_value="5th-order")
            dpg.add_spacer(height=_spcheight)
            btnTgtArr = dpg.add_button(label="设置目标阵列")
            # def _pop_target_array_win():
            #     # winTgtArr = dpg.add_window(label =)
            with dpg.window(label = "设置目标阵列", tag = "target array window",
                            pos = (200,200), width = 450, height=450,
                            show=False) as winTgtArr:
                dpg.add_input_text(tag = "binary target array",
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
            dpg.set_item_callback(btnTgtArr, lambda : dpg.configure_item(winTgtArr, show = True))
            # dpg.add_button(label="hello", tag = "hello", 
            #                callback= 
            #                _collect_awg_params
            #                )
# _collect_awg_params()
dpg.set_primary_window("win1", True)
frame_stack._update()
# dpg.show_style_editor()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
