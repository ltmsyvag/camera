#%%
import dearpygui.dearpygui as dpg
import threading
import time
import math
from mydpghelper import (
    _log, gui_open_cam, FrameStack, start_acqloop, 
    save_with_timestamp, _update_hist, extend_dpg_methods, MyPath)
dpg = extend_dpg_methods(dpg)
# from tiff_imports import flist
# frame_stack = FrameStack(flist)
frame_stack = FrameStack()
import tifffile


dpg.create_context()

_, bold_font, large_font = dpg.initialize_chinese_fonts()
toggle_decor = dpg.initialize_toggle_btn()
dpg.bind_custom_theming()

dpg.create_viewport(title='cam-AWG GUI', 
                    width=1000, height=1020, x_pos=0, y_pos=0,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571


with dpg.window(tag="win1", pos=(0,0)):
    # with dpg.group():
    with dpg.group(horizontal=True, height=720):
        with dpg.child_window(width=220):
            with dpg.group(horizontal=False):
                camSwitch = dpg.add_button(
                    width=150, height=70, user_data={
                        "is on" : False, 
                        "off label" : "相机已关闭",
                        "on label" : "相机已开启",
                        "camera object" : None, 
                        })

                acqToggle = dpg.add_checkbox(label = "采集循环开关", enabled=False,
                                            user_data=
                                            {
                                                "keep acquiring thread event" : threading.Event(),
                                                "acq loop thread" : None,
                                            })
                dpg.bind_item_font(dpg.last_item(), bold_font)
                def _toggle_acqloop_(sender, app_data, user_data):
                    state = app_data
                    eventKeepAcquiring = user_data["keep acquiring thread event"]
                    cam = dpg.get_item_user_data(camSwitch)["camera object"]
                    itemsToToggle = ["expo and roi fields", camSwitch]
                    if state:
                        threadAcq = threading.Thread(target=start_acqloop, args=(cam, eventKeepAcquiring, frame_stack))
                        user_data["acq loop thread"] = threadAcq
                        eventKeepAcquiring.set()
                        threadAcq.start()
                    else:
                        threadAcq = user_data["acq loop thread"]
                        eventKeepAcquiring.clear()
                        threadAcq.join()
                        user_data["acq loop thread"] = None
                        cam.stop_acquisition()
                        cam.set_trigger_mode("int")
                        print("acq loop stopped")
                    for item in itemsToToggle: # userproof: toggle the gray/ungray of some fields
                        dpg.configure_item(item, enabled = not state)
                    dpg.set_item_user_data(sender, user_data)
            dpg.set_item_callback(acqToggle, _toggle_acqloop_)
            dpg.add_separator()
            with dpg.group(tag = "expo and roi fields",horizontal=False, enabled=False) as groupExpoRoi:
                dpg.add_text("exposure time (ms):")
                fieldExpo = dpg.add_input_float(
                    width = 120, step=0, format="%.4f",
                    default_value= 100)
                def _setCamExpo(_, app_data, __): # the app_data in this case is the same as dpg.get_value(fieldExpo)
                    timeInMs, cam = app_data, dpg.get_item_user_data(camSwitch)["camera object"]
                    cam.set_exposure(timeInMs*1e-3)
                dpg.set_item_callback(fieldExpo, _setCamExpo)
                with dpg.item_handler_registry(tag="on Leaving fieldExpo"):
                    def _changeField(*callbackArgs):
                        cam = dpg.get_item_user_data(camSwitch)["camera object"]
                        camInternalExpoInMs = cam.cav["exposure_time"] * 1e3
                        dpg.set_value(fieldExpo, camInternalExpoInMs)
                    dpg.add_item_deactivated_after_edit_handler(callback= _changeField)
                dpg.bind_item_handler_registry(fieldExpo, "on Leaving fieldExpo")
                dpg.add_spacer(height=10)
                dpg.add_separator(label="ROI (max h 4096, v 2304)")
                dpg.add_text("h start & h length:", )
                fieldsROIh = dpg.add_input_intx(size=2, indent= 20,width=100, default_value=[1352, 240,0,0])
                dpg.add_text("v start & v length:")
                fieldsROIv = dpg.add_input_intx(size=2, indent = dpg.get_item_indent(fieldsROIh),width=dpg.get_item_width(fieldsROIh), default_value=[948,240,0,0])
                dpg.add_text("h binning & v binning")
                fieldsBinning = dpg.add_input_intx(size=2, indent = dpg.get_item_indent(fieldsROIh),width=dpg.get_item_width(fieldsROIh), default_value=[1,1,0,0])
                def do_set_cam_roi_using_6fields():
                    hstart, hwid, *_ = dpg.get_value(fieldsROIh)
                    vstart, vwid, *_ = dpg.get_value(fieldsROIv)
                    hbin, vbin, *_ = dpg.get_value(fieldsBinning)
                    cam = dpg.get_item_user_data(camSwitch)["camera object"]
                    cam.set_roi(hstart, hstart+hwid, vstart, vstart+vwid, hbin, vbin)
                def do_set_6fields_roi_using_cam(): # arg free callback, also indpendently used (not as callback) in cam switch initialization
                    cam = dpg.get_item_user_data(camSwitch)["camera object"]
                    hstart, hend, vstart, vend, hbin, vbin = cam.get_roi()
                    # print(hstart, hend, vstart, vend, hbin, vbin)
                    dpg.set_value(fieldsROIh,[hstart, hend-hstart,0,0])
                    dpg.set_value(fieldsROIv,[vstart, vend-vstart,0,0])
                    dpg.set_value(fieldsBinning,[hbin, vbin,0,0])
                with dpg.item_handler_registry(tag="on leaving 6 ROI fields"):
                    dpg.add_item_deactivated_after_edit_handler(callback=do_set_6fields_roi_using_cam)
                for _item in [fieldsROIh, fieldsROIv, fieldsBinning]:
                    dpg.set_item_callback(_item, do_set_cam_roi_using_6fields)
                    dpg.bind_item_handler_registry(_item, "on leaving 6 ROI fields")
            
        with dpg.child_window():
            # frame = _myRandFrame()
            with dpg.group(horizontal=True):
                fieldSavePath = dpg.add_input_text(hint="path to save tiff, e.g. C:\\Users\\username\\Desktop\\", width=600)
                btnLoad = dpg.add_button(label="load frames", callback=lambda: dpg.show_item("file dialog"))
                def _cb_(sender, app_data, user_data):
                    # print(type(app_data))
                    # for key, val in app_data.items():
                    #     print(key, "||",val)
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
                    pass
            with dpg.group(horizontal=True):        
                frameStackCnt = dpg.add_text(tag = "frame stack count display", default_value= "0 frames in stack")
                saveBtn = dpg.add_button(callback=_log, label="保存 frame stack", width=150, height=35)
                
                dpg.add_button(tag = "clear stack button", label="清空 frame stack", width=150, height=35)
                def _on_confirm():
                    frame_stack.clear()
                    dpg.set_value(frameStackCnt, "0 frames in stack")
                    dpg.delete_item("confirmation_modal")  # Close the modal after confirming

                def _on_cancel():
                    # print("Cancelled!")
                    dpg.delete_item("confirmation_modal")  # Close the modal after cancelling

                def _open_confirmation():
                    if not dpg.does_item_exist("confirmation_modal"):
                        with dpg.window(label="Confirm Action", pos=(200, 200),
                                        modal=True, tag="confirmation_modal", 
                                        width=300, height=150):
                            dpg.add_text("确认要清空内存中所有的 frames 吗？")
                            with dpg.group(horizontal=True):
                                dpg.add_button(label="Yes", width=75, callback=_on_confirm)
                                dpg.add_button(label="No", width=75, callback=_on_cancel)
                dpg.set_item_callback("clear stack button", _open_confirmation)
                btnSaveCurrent = dpg.add_button(label="保存当前 frame", width=150, height=35)
                def _saveCurrentFrame(*cbargs):
                    id = dpg.get_item_user_data(leftArr)
                    frame = frame_stack[id]
                    dpath = dpg.get_value(fieldSavePath)
                    notsaved = save_with_timestamp(dpath, frame, id)
                    if notsaved:
                        dpg.set_value(frameStackCnt, "NOT Saved!")
                    else:
                        dpg.set_value(frameStackCnt, "Saved!")
                dpg.set_item_callback(btnSaveCurrent, _saveCurrentFrame)
                def _leftArrCallback(sender, _, user_data):
                    id = user_data
                    if frame_stack.cid:
                        frame_stack.cid -= 1
                        frame_stack.plot_cid_frame()
                        # if id<0: id = 0
                        # plot_frame(frame_stack[id])
                        # print("re-plotted!")
                    dpg.set_item_user_data(sender, id)
                def _rightArrCallback(*cbargs):
                    id = dpg.get_item_user_data(leftArr)
                    if frame_stack and (frame_stack.cid<len(frame_stack)-1):
                        frame_stack.cid += 1
                        frame_stack.plot_cid_frame()
                        # if id >= len(frame_stack): id = len(frame_stack)-1
                        # plot_frame(frame_stack[id])
                    dpg.set_item_user_data(leftArr, id)
                dpg.bind_item_font(frameStackCnt, bold_font)
                def _saveFrame(*cbargs):
                    dpath = dpg.get_value(fieldSavePath)
                    notsaved = None
                    for id, frame in enumerate(frame_stack):
                        notsaved = save_with_timestamp(dpath, frame, id)
                        if notsaved:
                            dpg.set_value(frameStackCnt, "NOT Saved!")
                            break
                    if not notsaved:
                        frame_stack.clear()
                        dpg.set_value(frameStackCnt, "0 frames in stack")
                dpg.set_item_callback(saveBtn, _saveFrame)
            # def _printstuff(sender):
            #     print(dpg.get_value(sender))
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_checkbox(label = "manual scale", tag = "manual scale checkbox")
                dpg.add_input_intx(tag = "color scale lims",label = "color scale min & max (0-65535)", size = 2, width=120, default_value=[0,65535,0,0])
                dpg.add_spacer(width=10)
                with dpg.group(tag="frame browse arrows",horizontal=True):
                    leftArr = dpg.add_button(tag = "plot previous frame", label="<", width=30, height=30, arrow=True)
                    rightArr = dpg.add_button(tag = "plot next frame", label=">", width=30, height=30, arrow=True, direction=dpg.mvDir_Right)
                    dpg.set_item_callback(leftArr, _leftArrCallback)
                    dpg.set_item_callback(rightArr, _rightArrCallback)
                    #==========
                    # dpg.set_item_user_data(leftArr, len(frame_stack)-1)
                    # dpg.set_value(frameStackCnt, f"{len(frame_stack)} frames in stack")
                dpg.add_spacer(width=20)
                dpg.add_checkbox(label="stack 平均图",tag="toggle 积分/单张 map")
                def _toggle_cid_and_avg_map_(_, app_data,__):
                    if frame_stack:
                        if app_data:
                            dpg.configure_item("frame browse arrows", enabled=False)
                            frame_stack.plot_avg_frame()
                            # frameAvg = sum(frame_stack)/len(frame_stack)
                            # plot_frame(frameAvg)
                        else:
                            dpg.configure_item("frame browse arrows", enabled=True)
                            frame_stack.plot_cid_frame()
                            # id = dpg.get_item_user_data(leftArr)
                            # plot_frame(frame_stack[id])
                dpg.set_item_callback("toggle 积分/单张 map", _toggle_cid_and_avg_map_)
            with dpg.group(horizontal=True):
                _cmap = dpg.mvPlotColormap_Viridis
                dpg.add_colormap_scale(tag = "frame colorbar", min_scale=0,max_scale=65535, height=400)
                dpg.bind_colormap(dpg.last_item(), _cmap)
                _side = 600
                with dpg.plot(tag="frame plot",label = "frame", no_mouse_pos=False, height=_side, width=_side,
                              query=True, query_color=(255,0,0), max_query_rects=1, min_query_rects=0):
                    dpg.bind_colormap(dpg.last_item(), _cmap)
                    _xyaxeskwargs = dict(no_gridlines = True, no_tick_marks = True)
                    dpg.add_plot_axis(dpg.mvXAxis, tag = "frame xax", label= "h", opposite=True, **_xyaxeskwargs)
                    dpg.add_plot_axis(dpg.mvYAxis, tag= "frame yax", label= "v", invert=True, **_xyaxeskwargs)
                    def floorHalfInt(num: float) -> float: # 0.6, 0.5 -> 0.5; 0.4 -> -0.5
                        return math.floor(num-0.5) + 0.5
                    def ceilHalfInt(num: float) -> float: # -0.6,-0.5 -> -0.5; 0.4,0.5 ->0.5, 0.6 - > 1.5
                        return math.ceil(num+0.5) - 0.5
                    def _updateHistOnQuery(sender, app_data, user_data):
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
                    dpg.set_item_callback("frame plot",callback=_updateHistOnQuery)
    with dpg.child_window(): # 为了让下面的 hist binning field 可以自然地从一个 window 的左上角开始选取 h，v 坐标，所以这里设置一个 child window
        with dpg.plot(tag="hist plot", label = "hist", height=-1, width=-1, no_mouse_pos=True):
            dpg.add_plot_axis(dpg.mvXAxis, label = "converted counts ((<frame pixel counts>-200)*0.1/0.9)")
            dpg.add_plot_axis(dpg.mvYAxis, label = "frequency", tag = "hist plot yax")
        dpg.add_input_int(pos=(80,10), tag = "hist binning input",label="hist binning", width=80,
                          min_value=1, default_value=1, min_clamped=True)
dpg.set_primary_window("win1", True)
#==== camSwitch: camera power switch button
dpg.bind_item_font(camSwitch, large_font)


@toggle_decor("expo and roi fields", acqToggle)
def camSwitch_callback(sender, _, user_data):
    state, cam, = user_data["is on"], user_data["camera object"], 
    next_state = not state # state after toggle
    if next_state:
        # dpg.set_item_label(camSwitch,"开启中...")
        cam = gui_open_cam()
        user_data["camera object"] = cam
        dpg.set_item_user_data(sender, user_data) # store cam object
        ## make cam trig

        ## set cam exposure from field value, then refresh field by cam value
        expFieldValInMs = dpg.get_value(fieldExpo) 
        cam.set_exposure(expFieldValInMs*1e-3)
        expoCamValInS = cam.cav["exposure_time"]
        dpg.set_value(fieldExpo, expoCamValInS*1e3)
        
        do_set_cam_roi_using_6fields()
        do_set_6fields_roi_using_cam()
    else:
        # cam.stop_acquisition()
        cam.close(); print("=====cam closed")
        user_data["camera object"] = None
        dpg.set_item_user_data(sender, user_data)

@toggle_decor("expo and roi fields", acqToggle)
def _dummy_camSwitch_callback(_, __, user_data):
    state = user_data["is on"]
    next_state = not state # state after toggle
    if next_state:
        time.sleep(0.5)
    else:
        time.sleep(0.5)
 
# camSwitch_callback = _dummy_camSwitch_callback



dpg.set_item_callback(camSwitch,camSwitch_callback)
# frame_stack._update()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
