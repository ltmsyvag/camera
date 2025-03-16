#%%
import dearpygui.dearpygui as dpg
import numpy as np
from guihelplib import _setChineseFont, _log, ZYLconversion
from scipy.stats import poisson
import math

def floorHalfInt(num: float) -> float: # 0.6, 0.5 -> 0.5; 0.4 -> -0.5
    return math.floor(num-0.5) + 0.5
def ceilHalfInt(num: float) -> float: # -0.6,-0.5 -> -0.5; 0.4,0.5 ->0.5, 0.6 - > 1.5
    return math.ceil(num+0.5) - 0.5

nFluoPhotons, bg, ilim, jlim = 10000, 200, 240, 240
frameStack, nFrames = [], 1000

for _ in range(nFrames):
    atom1fluoXY = [(v,h) for v,h in zip(np.random.normal(20,3,nFluoPhotons), np.random.normal(50,3,nFluoPhotons))]
    frame = poisson.rvs(200, size = ilim*jlim).reshape((ilim,-1)).astype(np.uint16)

    for v,h in atom1fluoXY:
        i,j = int(v), int(h)
        if i>=0 and j>=0 and i<ilim and j<jlim:
            frame[i,j] += 1
    frameStack.append(frame)

fframe, _fmin, _fmax, (_nVrows, _nHcols) = frame.astype(float), frame.min(), frame.max(), frame.shape
# fframe = fframe[::-1]

dpg.create_context()
_setChineseFont(19)
dpg.create_viewport(title='test', 
                    width=600, height=800,vsync=False)

with dpg.window() as win1:
    with dpg.plot(label="Heat Series", no_mouse_pos=True, height=500, width=500,
                  query=True,max_query_rects=1, min_query_rects=0,query_color=(255,0,0),callback=_log) as thePlot:
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Viridis)
        dpg.add_plot_axis(dpg.mvXAxis, opposite=True)
        with dpg.plot_axis(dpg.mvYAxis, invert = True):
            dpg.add_heat_series(fframe,
                                _nVrows,_nHcols,
                                scale_min=_fmin, scale_max=_fmax,
                                bounds_min = (0,_nVrows), bounds_max = (_nHcols, 0),
                                format=""
                                )
    # with dpg.child_window() as win2:
    data = poisson.rvs(100, size = 100).tolist()
    def produceHistParams(data: list, binning: int = 1):
        themaxInt = int(max(data))
        nBins = themaxInt//binning+1
        max_range = nBins*binning
        return themaxInt, nBins, max_range
    _max, _nBins, max_range = produceHistParams(data, binning=1)
    # data = [0,0,0,1,1,2,3,4]
    dpg.add_input_int()
    with dpg.plot(label = "hist", height= -1, width=-1,no_mouse_pos=True):
        dpg.add_plot_axis(dpg.mvXAxis, label= "camera counts")
        with dpg.plot_axis(dpg.mvYAxis, label= "frequency") as yaxis:
            dpg.add_histogram_series(data, 
                                     bins=_nBins,
                                     max_range=max_range,
                                    #  bar_scale=2
                                     )
def _updateHist(hLhRvLvR: tuple, frameStack: list)->None:
    hLlim, hRlim, vLlim, vRlim = hLhRvLvR
    vidLo, vidHi = math.floor(vLlim), math.floor(vRlim)
    hidLo, hidHi = math.floor(hLlim), math.floor(hRlim)
    histData = []
    for frame in frameStack:
        frame = ZYLconversion(frame)
        subFrame = frame[vidLo:vidHi+1, hidLo:hidHi+1]
        histData.append(subFrame.sum())
    dpg.delete_item(yaxis, children_only=True)
    _, _nBins, max_range = produceHistParams(histData,binning=1)
    dpg.add_histogram_series(histData, parent=yaxis, bins = _nBins, max_range=max_range)


def _cb(sender, app_data, user_data):
    """
         h->
      #1------+
    v  |      |
    ↓  +-----#2
     app_data: (h1, v1, h2, v2)
    """
    if app_data:
        h1, v1, h2, v2 = app_data[0]
        # print(ceilHalfInt(h1),floorHalfInt(h2),ceilHalfInt(v1), floorHalfInt(v2))
        hLhRvLvR = hLlim, hRlim, vLlim, vRlim = ceilHalfInt(h1), floorHalfInt(h2), ceilHalfInt(v1), floorHalfInt(v2)
        if user_data and hLhRvLvR == user_data:
            pass
            # print("passed")
        else:
            dpg.set_item_user_data(thePlot, hLhRvLvR)
            if hLlim<=hRlim and vLlim <=vRlim: # if at least one rect center is selected
                _updateHist(hLhRvLvR, frameStack)
                # vidLo, vidHi = math.floor(vLlim), math.floor(vRlim)
                # hidLo, hidHi = math.floor(hLlim), math.floor(hRlim)
                # histData = []
                # for frame in frameStack:
                #     frame = ZYLconversion(frame)
                #     subFrame = frame[vidLo:vidHi+1, hidLo:hidHi+1]
                #     histData.append(subFrame.sum())
                #     # histData.append(int(subFrame.sum())) # int is somehow necessary for hist plotting
                # dpg.delete_item(yaxis, children_only=True)
                # # dpg.add_histogram_series(data, bins)
                # _, _nBins, max_range = produceHistParams(histData, binning=1)
                # dpg.add_histogram_series(histData, parent=yaxis,bins = _nBins, max_range=max_range)
    else:
        dpg.set_item_user_data(sender, None) # actions from other items cannot check app_data of this item directly (usually dpg.get_value(item) can check the app_data of an item, but not for this very special query rect coordinates app_data belonging to the heatmap plot!), so they check the user_data of this item. since I mean to stop any histogram updating when no query rect is present, then this no-rect info is given by user_data = None of the heatmap plot.


# def _cb(sender, app_data,user_data):
    ### print(user_data is None)
    # if not app_data:
    #     dpg.set_item_user_data(sender, None)
    #     print("user data cleared")
    # else:
    #     dpg.set_item_user_data(sender, "blah")
    #     print(dpg.get_item_user_data(sender))
dpg.set_item_callback(thePlot, callback=_cb)
dpg.set_primary_window(win1, True)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
# %%
