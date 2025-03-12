#%%
import dearpygui.dearpygui as dpg
from guihelplib import _setChineseFont, _myRandFrame, _feedTheAWG
import numpy as np
from codetiming import Timer
import time

dpg.create_context()
dpg.create_viewport(title='test', 
                    width=600, height=600,
                    vsync=False) # important option to dismiss input lab, see https://github.com/hoffstadt/DearPyGui/issues/1571

_setChineseFont(dpg, 19,19,19)
with dpg.window() as win1:
    frame = _myRandFrame(20, 240)
    fframe, _fmin, _fmax, (_nVrows, _nHcols) = frame.astype(float), frame.min(), frame.max(), frame.shape
    values = (0.8, 2.4, 2.5, 3.9, 0.0, 4.0, 0.0,
                2.4, 0.0, 4.0, 1.0, 2.7, 0.0, 0.0,
                1.1, 2.4, 0.8, 4.3, 1.9, 4.4, 0.0,
                0.6, 0.0, 0.3, 0.0, 3.1, 0.0, 0.0,
                0.7, 1.7, 0.6, 2.6, 2.2, 6.2, 0.0,
                1.3, 1.2, 0.0, 0.0, 0.0, 3.2, 5.1,
                0.1, 2.0, 0.0, 1.4, 0.0, 1.9, 6.3)
    # values = np.array(values, dtype=np.uint16)
    # _fmin, _fmax, _nVrows, _nHcols = 0,6.3,7,7
    print(frame.nbytes)
    # _fmin, _fmax = 50000,65535
    with dpg.group(horizontal=True):
        colorbar = dpg.add_colormap_scale(min_scale=_fmin, max_scale=_fmax, height=400)
        dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Hot)
        with dpg.plot(label="Heat Series", no_mouse_pos=True, height=400, width=-1):
            dpg.bind_colormap(dpg.last_item(), dpg.mvPlotColormap_Hot)
            _xyaxeskwargs = dict(no_gridlines = True, no_tick_marks = True)
            theXax = dpg.add_plot_axis(dpg.mvXAxis, label="h", opposite=True,
                              **_xyaxeskwargs)
            with dpg.plot_axis(dpg.mvYAxis, label="v", invert=True,
                               **_xyaxeskwargs) as theYax:
                with Timer():
                    dpg.add_heat_series(fframe,
                                        # 100,100,
                                        _nVrows, _nHcols,
                                        tag="heat_series",
                                        scale_min=_fmin, 
                                        scale_max=_fmax,
                                        bounds_min= (1,1),
                                        bounds_max= (_nHcols, _nVrows),
                                        format="")
                    _feedTheAWG(fframe)
    def _changefig(*callbackArgs):
        with Timer():
            frame = _myRandFrame(240, 240)
            fframe, _fmin, _fmax, (_nVrows, _nHcols) = frame.astype(float), frame.min(), frame.max(), frame.shape
            print(dpg.get_item_configuration(colorbar))
            dpg.configure_item(colorbar, min_scale =_fmin, max_scale=_fmax)
            dpg.delete_item(theYax, children_only=True) # this is necessary!
            dpg.add_heat_series(fframe, _nVrows, _nHcols, 
                                parent=theYax, 
                                scale_min=_fmin, 
                                scale_max=_fmax,
                                bounds_min= (1,1),
                                bounds_max= (_nHcols, _nVrows),
                                format="")
            dpg.fit_axis_data(theXax)
            dpg.fit_axis_data(theYax)
    dpg.add_button(label="change fig", callback=_changefig)


# print(dpg.get_item_configuration("heat_series"))
dpg.set_primary_window(win1, True)
dpg.setup_dearpygui()
dpg.show_viewport()

dpg.start_dearpygui()
dpg.destroy_context()