#%%
import dearpygui.dearpygui as dpg
import threading
import tifffile
from guihelplib import (
    _log, _setChineseFont,rgbOppositeTo, guiOpenCam, _myRandFrame,
      _feedTheAWG, startAcqLoop,plotFrame,)

dpg.create_context()

_, bold_font, large_font = _setChineseFont(dpg,
                                default_fontsize=19,
                                bold_fontsize=21,
                                large_fontsize=30)

dpg.create_viewport(title='cam-AWG GUI', 
                    width=1000, height=800,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571
with dpg.theme(label="global theme") as global_theme:
    with dpg.theme_component(dpg.mvAll): # online doc: theme components must have a specified item type. This can either be `mvAll` for all items or a specific item type
        # dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1, 
        #                     category=dpg.mvThemeCat_Core # online docstring paraphrase: you are mvThemeCat_core, if you are not doing plots or nodes. 实际上我发现不加这个 kwarg 也能产生出想要的 theme。但是看到网上都加，也就跟着加吧
        #                     )
        dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (255,255,0), category=dpg.mvThemeCat_Core)
dpg.bind_theme(global_theme)

with dpg.window(tag="win1", pos=(0,0)):
    with dpg.group(horizontal=True):
        with dpg.child_window(width=220):
            with dpg.group(horizontal=False):
                camSwitch = dpg.add_button(
                    width=150, height=70, user_data={
                        "is on" : False, 
                        "camera object" : None, 
                        "camera off label" : "相机已关闭",
                        "camera on label" : "相机已开启",
                        "camera off rgb" : (202, 33, 33),
                        "camera off hovered rgb" : (255, 0, 0),
                        "camera on rgb" : (25,219,72),
                        "camera on hovered rgb" : (0,255,0),
                        })

                _1 = dpg.get_item_user_data(camSwitch)
                dpg.set_item_label(camSwitch, _1["camera off label"])
                acqToggle = dpg.add_checkbox(label = "采集循环开关",callback=_log, enabled=False,
                                             user_data=
                                             {
                                                 "keep acquiring thread event" : threading.Event(),
                                                 "acq loop thread" : None,
                                              })
                dpg.bind_item_font(dpg.last_item(), bold_font)
                frameStack = []
                def _toggleAcqLoop(sender, app_data, user_data):
                    state = app_data
                    eventKeepAcquiring = user_data["keep acquiring thread event"]
                    cam = dpg.get_item_user_data(camSwitch)["camera object"]
                    itemsToToggle = ["expo and roi fields", camSwitch]
                    if state:
                        threadAcq = threading.Thread(target=startAcqLoop, args=(cam, eventKeepAcquiring, frameStack))
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
            dpg.set_item_callback(acqToggle, _toggleAcqLoop)
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
                def setCamROIfrom6Fields():
                    hstart, hwid, *_ = dpg.get_value(fieldsROIh)
                    vstart, vwid, *_ = dpg.get_value(fieldsROIv)
                    hbin, vbin, *_ = dpg.get_value(fieldsBinning)
                    cam = dpg.get_item_user_data(camSwitch)["camera object"]
                    cam.set_roi(hstart, hstart+hwid, vstart, vstart+vwid, hbin, vbin)
                def set6FieldsROIfromCAM(): # arg free callback, also indpendently used (not as callback) in cam switch initialization
                    cam = dpg.get_item_user_data(camSwitch)["camera object"]
                    hstart, hend, vstart, vend, hbin, vbin = cam.get_roi()
                    print(hstart, hend, vstart, vend, hbin, vbin)
                    dpg.set_value(fieldsROIh,[hstart, hend-hstart,0,0])
                    dpg.set_value(fieldsROIv,[vstart, vend-vstart,0,0])
                    dpg.set_value(fieldsBinning,[hbin, vbin,0,0])
                with dpg.item_handler_registry(tag="on leaving 6 ROI fields"):
                    dpg.add_item_deactivated_after_edit_handler(callback=set6FieldsROIfromCAM)
                for _item in [fieldsROIh, fieldsROIv, fieldsBinning]:
                    dpg.set_item_callback(_item, setCamROIfrom6Fields)
                    dpg.bind_item_handler_registry(_item, "on leaving 6 ROI fields")
            
        with dpg.child_window():
            # frame = _myRandFrame()
            fieldSavePath = dpg.add_input_text(hint="path to save tiff, e.g. C:\\Users\\username\\Desktop\\", width=600)
            with dpg.group(horizontal=True):
                frameStackCnt = dpg.add_text(tag = "frame stack count display", default_value= "0 frames in stack")
                saveBtn = dpg.add_button(callback=_log, label="保存 frame stack", width=150, height=35)
                dpg.add_spacer(width=30)
                leftArr = dpg.add_button(tag = "plot previous frame", label="<", width=30, height=30, arrow=True)
                rightArr = dpg.add_button(tag = "plot next frame", label=">", width=30, height=30, arrow=True, direction=dpg.mvDir_Right)
                def _leftArrCallback(sender, _, user_data):
                    id = user_data
                    if frameStack:
                        id -= 1
                        if id<0: id = 0
                        plotFrame(frameStack[id])
                        # print("re-plotted!")
                    dpg.set_item_user_data(sender, id)
                def _rightArrCallback(*args):
                    id = dpg.get_item_user_data(leftArr)
                    if frameStack:
                        id += 1
                        if id >= len(frameStack): id = len(frameStack)-1
                        plotFrame(frameStack[id])
                    dpg.set_item_user_data(leftArr, id)
                dpg.set_item_callback(leftArr, _leftArrCallback)
                dpg.set_item_callback(rightArr, _rightArrCallback)
                dpg.bind_item_font(frameStackCnt, bold_font)
                def _saveFrame(*_callbackArgs):
                    path = dpg.get_value(fieldSavePath)
                    for id, frame in enumerate(frameStack):
                        fpath = path + f"{id}.tiff"
                        tifffile.imwrite(fpath, frame)
                    frameStack.clear()
                    dpg.set_value(frameStackCnt, "0 frames in stack")
                dpg.set_item_callback(saveBtn, _saveFrame)
            with dpg.group(horizontal=True):
                _cmap = dpg.mvPlotColormap_Hot
                dpg.add_colormap_scale(tag = "frame colorbar", min_scale=0,max_scale=65535, height=400)
                dpg.bind_colormap(dpg.last_item(), _cmap)
                _side = 600
                with dpg.plot(tag="frame plot",label = "frame", no_mouse_pos=True, height=_side, width=_side):
                    dpg.bind_colormap(dpg.last_item(), _cmap)
                    _xyaxeskwargs = dict(no_gridlines = True, no_tick_marks = True)
                    dpg.add_plot_axis(dpg.mvXAxis, tag = "frame xax", label= "h", opposite=True, **_xyaxeskwargs)
                    axCmap = dpg.add_plot_axis(dpg.mvYAxis, tag= "frame yax", label= "v", invert=True, **_xyaxeskwargs)
                # with dpg.plot(label="frame", no_mouse_pos=True, height=400, width=-1):
                #     dpg.add_plot_axis(dpg.mvXAxis, label="x", lock_min=True, lockmax=True, no_gridlines=True,no_tick_marks=True)
                #     with dpg.plot_axis(dpg.mvYAxis,label="y", lock_min=True, lockmax=True, no_gridlines=True, no_tick_marks=True):
                #         dpg.add_heat_series(frame,7)
dpg.set_primary_window("win1", True)

#==== camSwitch: camera power switch button
dpg.bind_item_font(camSwitch, large_font)

## 设置 cam switch 开关的 theme
_1 = dpg.get_item_user_data(camSwitch)["camera on rgb"]
_2 = dpg.get_item_user_data(camSwitch)["camera off rgb"]
_3 = dpg.get_item_user_data(camSwitch)["camera on hovered rgb"]
_4 = dpg.get_item_user_data(camSwitch)["camera off hovered rgb"]
with dpg.theme(label="cam switch ON") as camONbtn_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _1, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _3, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _3, category=dpg.mvThemeCat_Core) 
        dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_1), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15, category=dpg.mvThemeCat_Core)
with dpg.theme(label="cam switch OFF") as camOFFbtn_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_Button, _2, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, _4, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, _4, category=dpg.mvThemeCat_Core)
        # dpg.add_theme_color(dpg.mvThemeCol_Text, rgbOppositeTo(*_2), category=dpg.mvThemeCat_Core) 
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 15, category=dpg.mvThemeCat_Core)

def camSwitch_callback(sender, _, user_data):
    state, cam, camONlabel, camOFFlabel = user_data["is on"], user_data["camera object"], user_data["camera on label"], user_data["camera off label"]
    state = not state # flip the state
    if state:
        dpg.set_item_label(camSwitch,"开启中...")
        cam = guiOpenCam()
        user_data["camera object"] = cam; dpg.set_item_user_data(sender, user_data) # push the cam object to the switch button user_data, to be used by the initial cam settings from the fields below

        ## make cam trig

        ## set cam exposure from field value, then refresh field by cam value
        expFieldValInMs = dpg.get_value(fieldExpo) 
        cam.set_exposure(expFieldValInMs*1e-3)
        expoCamValInS = cam.cav["exposure_time"]
        dpg.set_value(fieldExpo, expoCamValInS*1e3)
        
        setCamROIfrom6Fields()
        set6FieldsROIfromCAM()
        dpg.set_item_label(sender, camONlabel)
        dpg.bind_item_theme(sender, camONbtn_theme)
    else:
        # cam.stop_acquisition()
        cam.close(); print("=====cam closed")
        cam = None
        dpg.set_item_label(sender, camOFFlabel)
        dpg.bind_item_theme(sender, camOFFbtn_theme)
    itemsToToggle = ["expo and roi fields", acqToggle]
    for item in itemsToToggle:
        dpg.configure_item(item, enabled=state)
    user_data["is on"] = state
    dpg.set_item_user_data(sender, user_data)
    # if state:
    #     prepCamForTrigAndPlot(cam)


dpg.set_item_callback(camSwitch,camSwitch_callback)
dpg.bind_item_theme(camSwitch, camOFFbtn_theme)

# print(dpg.get_value(fieldExpo))
# dpg.show_style_editor()
# dpg.show_item_registry()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
