"""
camgui 相关的帮助函数
"""
#%%
camgui_ver = '1.3'
import pandas as pd
from itertools import cycle
from collections import namedtuple, deque
import multiprocessing.connection
DupeMap = namedtuple(typename='DupeMap', # class for useful dpg items in a dupe heatmap window
                        field_names=[
                            'pltSlv',
                            'pltMstr',
                            'yAxSlv',
                            'yAxMstr',
                            'inputInt',
                            'radioBtn',
                            'cBox'])
import json
import traceback
import multiprocessing
import queue
import time
import copy
import numpy.typing as npt
from typing import List, Dict, Sequence, Tuple
import re
from deprecated import deprecated
import math
from datetime import datetime
from pylablib.devices import DCAM
import numpy as np
import threading
import colorsys
import tifffile
from .utils import MyPath, UserInterrupt, camgui_params_root, _mk_save_tree_from_root_to_day, find_latest_sesframes_folder, find_newest_daypath_in_save_tree
import dearpygui.dearpygui as dpg
import platform
import uuid
# system = platform.system()
# if (system == "Windows") and (hex(uuid.getnode()) != '0xf4ce2305b4c7'): # code is A402 computer
import spcm
from AWG_module.no_with_func import DDSRampController
from AWG_module.unified import feed_AWG

class FrameDeck(list):
    """
    class of a special list with my own methods for manipulating the frames it stores
    """
    def __init__(self, *args, **kwargs):
        """
        将状态变量作为 instance attr 初始化
        好处(相对于 class attr 来说)是在不重启 kernel, 只重启 camgui.py 的情况下,
        frame_deck 的状态不会保留上一次启动的记忆
        """
        super().__init__(*args, **kwargs) # make sure I do not override the parent dunder init
        self.cid: int | None = None # current heatmap's id in deck
        self.float_deck: List[npt.NDArray[np.floating]] = [] # gui 中的操作需要 float frame, 因此与 list (int deck) 对应, 要有一个 float deck
        self.frame_avg: npt.NDArray[np.floating] | None = None
        self.lst_dupe_maps : List[DupeMap] = [] # 保存 duplicated heatmaps window 中的 item tuple
        self.seslabel_deck: List[str] = []
        self.dict_dr : Dict[int, None|Dict[str, pd.DataFrame|Sequence[float]]] = dict() # drag rect dict, {<group number> : <dict of two items: {'grp dr df' : <dataframe of dr tags, row-indexed by yaxes, col-named by uuid>}, {'fence' : (xmin, xmax, vmin, vmax)}, which is the group fence>}
        # self.series_id_gen= count() # guarantee a unique id as col name for each dr series in the per-group dataframes in self.dict_dr
        self.dq100 = deque(maxlen=100) # 保存最近100次添加的 dr series 的信息, 用于批量添加阵列 dr

        def tab_10_spTheme_factory(color_id :int):
            with dpg.theme() as spTheme:
                sp_rgb = self.get_dr_color_in_group(color_id)
                with dpg.theme_component(dpg.mvSimplePlot):
                    dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, sp_rgb + [255], category=dpg.mvThemeCat_Core) # yes, simple plot's color's cat is core, not plot!! can plot cat would induce error!
                    dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, rgb_opposite(*sp_rgb), category=dpg.mvThemeCat_Core) # yes, simple plot's color's cat is core, not plot!! can plot cat would induce error!
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (255,255,0), category=dpg.mvThemeCat_Core)
            return spTheme
        self.tab_10_spThemes = [tab_10_spTheme_factory(i) for i in range(10)]

        self.lock = threading.RLock()
        self.hsformat = '' # heat series format

        self.ihrTableCellText = dpg.add_item_handler_registry()
        def bring_out_hist_plot(_, app_data, __):
            _, textTag = app_data
            textTag = dpg.get_item_alias(textTag)
            grp_id: str = textTag.split('-')[-1]
            winTag = 'window hist-' + grp_id
            if dpg.does_item_exist(winTag):
                dpg.configure_item(winTag, collapsed=False)
                dpg.focus_item(winTag)
            else:
                with dpg.window(tag = winTag, label = grp_id, width = 500, height=300, on_close=lambda sender: dpg.delete_item(sender), no_saved_settings=True):
                    with dpg.plot(tag = 'plot hist-'+grp_id, no_mouse_pos=True, width=-1, height=-1):
                        dpg.bind_colormap(dpg.last_item(), dict_cmap_tab20_segmented[int(grp_id)%10])
                        dpg.add_plot_axis(dpg.mvXAxis, label = 'converted counts ((<frame pixel counts>-200)*0.1/0.9)')
                        dpg.add_plot_axis(dpg.mvYAxis, label = 'frequency', tag = 'yax hist-'+grp_id)
                self._update_one_hist(int(grp_id))
        tab20_colors = ((0.12156862745098039, 0.4666666666666667, 0.7058823529411765),
                        (0.6823529411764706, 0.7803921568627451, 0.9098039215686274),
                        (1.0, 0.4980392156862745, 0.054901960784313725),
                        (1.0, 0.7333333333333333, 0.47058823529411764),
                        (0.17254901960784313, 0.6274509803921569, 0.17254901960784313),
                        (0.596078431372549, 0.8745098039215686, 0.5411764705882353),
                        (0.8392156862745098, 0.15294117647058825, 0.1568627450980392),
                        (1.0, 0.596078431372549, 0.5882352941176471),
                        (0.5803921568627451, 0.403921568627451, 0.7411764705882353),
                        (0.7725490196078432, 0.6901960784313725, 0.8352941176470589),
                        (0.5490196078431373, 0.33725490196078434, 0.29411764705882354),
                        (0.7686274509803922, 0.611764705882353, 0.5803921568627451),
                        (0.8901960784313725, 0.4666666666666667, 0.7607843137254902),
                        (0.9686274509803922, 0.7137254901960784, 0.8235294117647058),
                        (0.4980392156862745, 0.4980392156862745, 0.4980392156862745),
                        (0.7803921568627451, 0.7803921568627451, 0.7803921568627451),
                        (0.7372549019607844, 0.7411764705882353, 0.13333333333333333),
                        (0.8588235294117647, 0.8588235294117647, 0.5529411764705883),
                        (0.09019607843137255, 0.7450980392156863, 0.8117647058823529),
                        (0.6196078431372549, 0.8549019607843137, 0.8980392156862745))
        dict_cmap_tab20_segmented = dict()
        with dpg.colormap_registry(): # 两个一组, 将 tab20 分成十份. 每个 cmap 的两种深, 浅颜色将在 hist plot 刷新时来回切换, 以明确 update 进程
            dict_cmap_tab20_segmented[0] = dpg.mvPoltColormap_tab20seg0 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[:2]], qualitative=True)
            dict_cmap_tab20_segmented[1] = dpg.mvPoltColormap_tab20seg1 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[2:4]], qualitative=True)
            dict_cmap_tab20_segmented[2] = dpg.mvPoltColormap_tab20seg2 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[4:6]], qualitative=True)
            dict_cmap_tab20_segmented[3] = dpg.mvPoltColormap_tab20seg3 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[6:8]], qualitative=True)
            dict_cmap_tab20_segmented[4] = dpg.mvPoltColormap_tab20seg4 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[8:10]], qualitative=True)
            dict_cmap_tab20_segmented[5] = dpg.mvPoltColormap_tab20seg5 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[10:12]], qualitative=True)
            dict_cmap_tab20_segmented[6] = dpg.mvPoltColormap_tab20seg6 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[12:14]], qualitative=True)
            dict_cmap_tab20_segmented[7] = dpg.mvPoltColormap_tab20seg7 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[14:16]], qualitative=True)
            dict_cmap_tab20_segmented[8] = dpg.mvPoltColormap_tab20seg8 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[16:18]], qualitative=True)
            dict_cmap_tab20_segmented[9] = dpg.mvPoltColormap_tab20seg9 = dpg.add_colormap([[int(r*255), int(g*255), int(b*255), 255] for (r,g,b) in tab20_colors[18:]], qualitative=True)

        dpg.add_item_double_clicked_handler(parent = self.ihrTableCellText, callback = bring_out_hist_plot)
    def memory_report(self) -> str:
        len_deck = len(self)
        if len_deck>0:
            mbsize_int_frames = sum([frame.nbytes for frame in self])/(1024**2)
            mbsize_float_frames = sum([frame.nbytes for frame in self])/(1024**2)
            size = mbsize_int_frames + mbsize_float_frames
        else:
            size = 0
        return  f"已绘制: {len_deck} 帧 ({size:.2f} MB); 缓存中: {_local_buffer.qsize()} 帧"
    @staticmethod
    def _make_savename_stub():
        """
        如果想保存的文件时间是
        "C:\\Users\\username\\Desktop\\2023-10-01-12-00-00_id.tiff",
        那么在 Desktop 存在并可写入, 且 frame deck 非空的情况下, 返回字符串形式的 stub
        "C:\\Users\\username\\Desktop\\2023-10-01-12-00-00"
        """
        dpath = MyPath(dpg.get_value("save path input field"))
        dpath.mkdir(parents=True, exist_ok=True)
        if dpath.is_dir() and dpath.is_writable():
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            fpath_stub = str(dpath / timestamp)
            return fpath_stub
        else:
            push_log("输入的路径有问题", is_error=True)
            raise UserInterrupt # 人工阻止后续程序运行. 因为 cb 是单独的线程, 所以 gui 不会崩
    def append(self, frame: np.ndarray):
        """
        append a new frame to int & float decks
        同时执行: 
        - cid update
        - 平均 heatmap 计算
        - counts display update
        - cid indicator updates
        append 现在貌似是为 frame_deck 添加 frame 的唯一入口, let's keep it that way
        """
        # print(frame.dtype)
        with self.lock:
            assert frame.dtype == np.uint16, "frame should be uint16, something's off?!"
            super().append(frame)
            fframe = frame.astype(float)
            self.float_deck.append(fframe)
            self.cid = len(self) - 1
            if self.cid == 0:
                self.frame_avg = fframe
            else:
                self.frame_avg = (self.frame_avg*(len(self)-1) + fframe)/len(self)
            dpg.set_value("frame deck display", self.memory_report())
            dpg.set_item_label("cid indicator", f"{self.cid}")
    def save_deck(self)->None:
        """
        保存全部 frames, 并 push 成功/失败 message
        """
        with self.lock:
            fpath_stub = self._make_savename_stub()
            if self:
                push_log('开始保存帧', is_warning=True)
                for i, frame in enumerate(self):
                    fpath = fpath_stub + f"_{i}.tif"
                    try:
                        tifffile.imwrite(fpath, frame)
                    except Exception:
                        push_exception(f"帧 #{i} 保存失败.")
                    
                push_log('已绘制的全部帧保存成功', is_good=True)
            else:
                push_log('没有任何已绘制的帧可供保存', is_error=True)
    def save_cid_frame(self)->None:
        """
        保存 cid 指向的 frame, 并 push 成功/失败 message
        """
        with self.lock:
            fpath_stub = self._make_savename_stub()
            if self.cid: # 当前 cid 不是 None, 则说明 deck 非空
                fpath = fpath_stub + f"_{self.cid}.tif"
                try:
                    tifffile.imwrite(fpath, self[self.cid])
                except Exception:
                    push_exception('当前已绘制帧保存失败')
                    return
                push_log('当前已绘制帧保存成功', is_good=True)
            else:
                push_log('没有任何已绘制的帧可供保存', is_error=True)
    def _find_lastest_sesframes_folder_and_save_frame(self)-> str:
        with self.lock:
            dpath_ses = find_latest_sesframes_folder() # produces UserInterrupt if folder seeking fails
            str_ses = str(dpath_ses.name)
            now = datetime.now()
            timestamp: str = now.strftime("%Y-%m-%d-%H-%M-%S-") + f"{now.microsecond//1000:03d}"
            fpath = dpath_ses /( timestamp + ".tif")
            try: # again, this is a redundant check, I don't think the save will fail, unless there's a Z disk connection problem
                tifffile.imwrite(fpath, self[self.cid])
                return str_ses
            except Exception:
                push_exception("当前帧保存失败")
                raise UserInterrupt
    def clear_deck(self)->None:
        """
        - clear int & float decks
        - cid update
        - avg frame update
        - clear ses label deck
        - cid indicator updates
        - clear all plots
        - clear all plot labels
        - clear local buffer (consumer 线程异常停止时，可以清空未使用的毒药丸)
        """
        with self.lock:
            super().clear()
            self.float_deck.clear()
            self.cid = None
            self.frame_avg = None
            self.seslabel_deck = []
            while not _local_buffer.empty():
                _local_buffer.get()
            dpg.set_value("frame deck display", self.memory_report())
            dpg.set_item_label("cid indicator", "N/A")
            lst1, lst2, _ = self.get_all_maptags()
            for yax in (lst1+lst2):  # clear heatmaps in all slaves, corner scatter points in all masters
                dpg.delete_item(yax, children_only=True)
                # print('yax', yax)
                thisPlot = dpg.get_item_parent(yax)
                dpg.configure_item(thisPlot, label = ' ')
    def get_all_maptags(self):
        lst_allyaxes_slv = [map.yAxSlv for map in self.lst_dupe_maps]
        lst_allyaxes_slv.append('frame yax')
        lst_allyaxes_mstr = [map.yAxMstr for map in self.lst_dupe_maps]
        lst_allyaxes_mstr.append('rects yax')
        lst_allplots_mstr = [dpg.get_item_parent(yax) for yax in lst_allyaxes_mstr]
        # lst_allplots_mstr = [map.pltMstr for map in self.lst_dupe_maps]
        return lst_allyaxes_slv, lst_allyaxes_mstr, lst_allplots_mstr
    # @staticmethod
    def _plot_frame(self, frame: npt.NDArray[np.floating], 
                    # xax: str="frame xax", 
                    yaxSlave: str | int, 
                    yaxMaster: str | int)->None:
        with self.lock:
            assert np.issubdtype(frame.dtype, float), 'heatmap frame can only be float!'
            colorbar='frame colorbar'
            fmin, fmax, (nvrows, nhcols) = frame.min(), frame.max(), frame.shape
            plot_mainframe_p = yaxSlave == 'frame yax' # need this check because we can plot in dupe frame windows
            if dpg.get_value('manual scale checkbox'):
                fmin, fmax, *_ = dpg.get_value('color scale lims')
            elif plot_mainframe_p: # update disabled manual color lim fields. do not do this when plotting elsewhere
                dpg.set_value('color scale lims', [int(fmin), int(fmax), 0, 0])
            else: # 在 dupe heatmap 中 plot 时, 啥都不干
                pass
            
            if plot_mainframe_p: # always update color bar lims when doing main plot, whether the manual scale checkbox is checked or not
                dpg.configure_item(colorbar, min_scale = fmin, max_scale = fmax)
            
            had_series_child_p = dpg.get_item_children(yaxSlave)[1] # plot new series 之前 check 是否有老 series
            if had_series_child_p:
                dpg.delete_item(yaxSlave, children_only=True) # this is necessary!
            dpg.add_heat_series(frame, nvrows, nhcols, parent=yaxSlave,
                                scale_min=fmin, scale_max=fmax,format=self.hsformat,
                                bounds_min= (0,nvrows), bounds_max= (nhcols, 0)
                                )
            """
            如果 frame 是:
            [[0,0,0],
            [0,0,0],
            [1,0,0],]
            用默认 axes (对于 xax, yax, 均有 opposite = False, invert = False)
            记 xbeg, ybeg = bounds_min; xend, yend = bounds_max, 
            根据 x(y)beg(end) 的不同选取, 可以有:
                                y
                                ^
                                |0 0 0 <- (xend = 2, yend = 2)
                                |0 0 0
            (xbeg = 0, ybeg = 0) ->|1 0 0
                                o-----> x

                                    y
                                    ^
                                    0|   0    0 <- (xend = 10, yend = 10)
                                    |
                                    |
                                    0|   0    0
                                    |
                                    o---------> x
            (xbeg = -1, ybeg = -1) -> 1    0    0

                                    y
                                    ^
            (xbeg = -1, ybeg = 10) -> 1|   0    0
                                    |
                                    |
                                    0|   0    0
                                    |
                                    o---------> x
                                    0    0    0 <- (xend = 10, yend=-1)

            当有 y 轴翻反转的情况 (x轴 `opposite=True`, 即将 visual 的 x 轴放到 frame 顶部;
            y 轴 `invert = True`, 即 y 轴刻度从上往下增长), 那么坐标变为
            o---> x
            |
            |
            v
            y
            但是 frame 呈现的原则依然同上, 和坐标系无关, 
            仅仅是初始点坐标(xbeg, ybeg)和末尾点的坐标(xend, yend)需要用新坐标系的相应值来表示
            """
            ### below is the corner scatter (master) plot associated with the slave plot above
            if had_series_child_p: # if had series child, then also had scatter child
                # scatterChild = dpg.get_item_children(yaxMaster)[1]
                dpg.delete_item(yaxMaster, children_only=True)
            # print(yaxMaster)
            scatterSeries = dpg.add_scatter_series(
                [0,0,nhcols, nhcols], [0, nvrows, 0, nvrows], parent=yaxMaster)
            with dpg.theme() as scatterThm:
                with dpg.theme_component(dpg.mvScatterSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, (0,255,0,0), category=dpg.mvThemeCat_Plots)
                    dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, (0,0,0,0), category=dpg.mvThemeCat_Plots)
            dpg.bind_item_theme(scatterSeries, scatterThm)
    def plot_avg_frame(self, yaxSlave= "frame yax", yaxMaster = 'rects yax'):
        """
        与 plot_cid_frame 一起都是 绘制 main heatmap 的方法
        区别于 plot_frame_dwim (绘制所有 map, 包括 dupe maps)
        x/yax kwargs make it possible to plot else where when needed
        """
        if self.frame_avg is not None:
            with self.lock:
                frame = self.frame_avg
            self._plot_frame(frame, yaxSlave, yaxMaster)
            for yax in [yaxSlave, yaxMaster]:
                thePlot = dpg.get_item_parent(yax)
                dpg.configure_item(thePlot, label = '已绘制所有帧的平均')
    def plot_cid_frame(self, yaxSlave= 'frame yax', yaxMaster = 'rects yax'):
        """
        与 plot_avg_frame 一起都是 绘制 main heatmap 的方法
        区别于 plot_frame_dwim (绘制所有 map, 包括 dupe maps)
        x/yax kwargs make it possible to plot else where when needed
        """
        if self.cid is not None:
            with self.lock:
                frame = self.float_deck[self.cid]
            self._plot_frame(frame, yaxSlave, yaxMaster)
            for yax in [yaxSlave, yaxMaster]:
                thePlot = dpg.get_item_parent(yax)
                dpg.configure_item(thePlot, label = self.seslabel_deck[self.cid])
    def plot_frame_dwim(self):
        """
        global update of all maps (main and dupes)
        """
        if dpg.get_value("toggle 积分/单张 map"):
            self.plot_avg_frame()
        else:
            self.plot_cid_frame()
        for dupe_map_items in self.lst_dupe_maps: # update dupe windows
            self._update_dupe_map(dupe_map_items)
    def _update_dupe_map(self, dupe_map: DupeMap,
                        #   yax, inputInt, radioBtn, cBox
                          ):
        """
        根据 duplicated map 的帧序号输入和 radio button 选择, 在给定的 xax, yax 中重绘热图
        这是搭配 lst_dupe_maps 使用的函数
        """
        input_id = dpg.get_value(dupe_map.inputInt)
        radio_option = dpg.get_value(dupe_map.radioBtn)
        plot_avg_p = dpg.get_value(dupe_map.cBox)
        if plot_avg_p:
            self.plot_avg_frame(dupe_map.yAxSlv, dupe_map.yAxMstr)
        else:
            if radio_option == "正数帧":
                plot_id = input_id
            else:
                plot_id = input_id+len(self) - 1
            if 0 <= plot_id < len(self):
                with self.lock:
                    frame = self.float_deck[plot_id]
                self._plot_frame(frame, dupe_map.yAxSlv, dupe_map.yAxMstr) # 不能用 plot_cid_frame 抽象, 因为这里不是 plot cid, 而是任意指定的 id
                label= self.seslabel_deck[plot_id]
            else:
                for yax in [dupe_map.yAxSlv, dupe_map.yAxMstr]:
                    dpg.delete_item(yax, children_only=True)
                label =  ' '
            for yax in [dupe_map.yAxSlv, dupe_map.yAxMstr]:
                thePlot = dpg.get_item_parent(yax)
                dpg.configure_item(thePlot, label=label)
    def _append_save_plot(self, this_frame: npt.NDArray[np.uint16]):
        """
        在单线程无并发时, 本函数是重排(如果 awg 开启)后的全套任务
        在双线程/双进程并发中, 本函数是 consumer 取得 frame 后的全套任务
        """
        beg = time.time()
        self.append(this_frame)
        if dpg.get_value("autosave"):
            try:
                str_ses = self._find_lastest_sesframes_folder_and_save_frame()
                self.seslabel_deck.append(str_ses)
            except UserInterrupt:
                self.seslabel_deck.append('未保存!')
        else:
            self.seslabel_deck.append('未保存!')
        self.plot_frame_dwim()
        self.update_hist_sheet()
        end = time.time()
        push_log(f"绘图和存储耗时{(end-beg)*1e3:.3f} ms")
    @staticmethod
    def get_dr_color_in_group(grp_id):
        rgb_lst_tab10 = ((0.12156862745098039, 0.4666666666666667, 0.7058823529411765), # 本来用 plt.get_cmap('tab10').colors, 改为直接用颜色数值,少 import一个包
                        (1.0, 0.4980392156862745, 0.054901960784313725),
                        (0.17254901960784313, 0.6274509803921569, 0.17254901960784313),
                        (0.8392156862745098, 0.15294117647058825, 0.1568627450980392),
                        (0.5803921568627451, 0.403921568627451, 0.7411764705882353),
                        (0.5490196078431373, 0.33725490196078434, 0.29411764705882354),
                        (0.8901960784313725, 0.4666666666666667, 0.7607843137254902),
                        (0.4980392156862745, 0.4980392156862745, 0.4980392156862745),
                        (0.7372549019607844, 0.7411764705882353, 0.13333333333333333),
                        (0.09019607843137255, 0.7450980392156863, 0.8117647058823529))
        this_color = rgb_lst_tab10[grp_id % 10]
        return [225*e for e in this_color]
    @staticmethod
    def ensure_minmax_order(
            xmin : float, 
            ymin : float, 
            xmax : float, 
            ymax : float
            ) -> Tuple[float]:
        """
        dpg.get_value(<drag rect tag>) 返回的 tuple (xmin, ymin, xmax, ymax) 可能会有 min max 反转的情况,
        本函数用于保证 min 是 min, max 是 max
        """
        if xmin>xmax:
            xmin, xmax = xmax, xmin
        if ymin>ymax:
            ymin, ymax = ymax, ymin
        return xmin, ymin, xmax, ymax
    @staticmethod
    def ensure_1x1_area(
            x1 : float, 
            y1 : float, 
            x2 : float, 
            y2 : float,
            ) -> Tuple[float]:
        x1r, y1r, x2r, y2r = round(x1), round(y1), round(x2), round(y2)
        if len(set([x1r, y1r, x2r, y2r])) < 4:
            if abs(y1 - y2) < 0.5:
                if int(y2) == y2:
                    y1r = y2+1 if y1>y2 else y2-1
                else:
                    y2r = y1+1 if y1<y2 else y1-1
            if abs(x1 - x2) < 0.5:
                if int(x2) == x2:
                    x1r = x2+1 if x1>x2 else x2-1
                else:
                    x2r = x1+1 if x1<x2 else x1-1
        return x1r, y1r, x2r, y2r
    def update_fences(self):
        for grp_id, ddict in self.dict_dr.items():
            if ddict is not None:
                self._update_grp_fence(grp_id)
    def _update_grp_fence(self, grp_id: int):
        """
        在保证当前 grp_id 存在并且 grp 不为空时才能使用
        """
        ddict = self.dict_dr[grp_id]
        dr_row = ddict['grp dr df'].iloc[0, :] # 取第一行 drag rects, 代表了单张热图上的本组的所有 dr, 其他行(热图)上的 dr 都是同步的, 因此不用考虑
        arr_minxminymaxxmaxy = np.array([
            self.ensure_minmax_order(*dpg.get_value(tag)) for tag in dr_row
        ])
        xmin, ymin, _, _ = arr_minxminymaxxmaxy.min(axis=0)
        _, _, xmax, ymax = arr_minxminymaxxmaxy.max(axis=0)
        ddict['fence'] = xmin, ymin, xmax, ymax
    def sync_dr_series_update_mrh(self, sender, _, user_data):
        # 第一部分, sync 其他热图中 dr 的 resize
        sender_pos = dpg.get_value(sender)
        grp_id, series_id = user_data
        ddict = self.dict_dr[grp_id]
        dr_series = ddict['grp dr df'][series_id]
        for drTag in dr_series:
            if drTag != sender:
                dpg.set_value(drTag, sender_pos)
        # 第二部分, 将正在拖拽的 drTag 放入 mouse release handler 的 user data 中, 供 mouse release handler 获取, 在释放 mouse 的时候进行 snapping
        mrh_dict = dpg.get_item_user_data('mouse release handler')
        if mrh_dict['dr being dragged'] is None: # dr 拖动时 callback 会被频繁触发, 需要避免反复写入 sender 这样可能好一些
            mrh_dict['dr being dragged'] = sender # 记录当前被拖动的 dr tag
    def add_dr_to_loc(self, 
                        xmean_dr : float, 
                        ymean_dr : float,
                        sidex: float = 1,
                        sidey: float = 1,
                        always_new_grp: bool = False, # if True, 新添加的 dr 总是融入进一个新的组(或占据一个旧的空组), 不尝试判断是否能融入现存 dr 组的 fence 中
                        update_hist_p =False,
                      ) -> Tuple[int, str]:
        """
        给定 drag rect 中心坐标 xmean_dr, ymean_dr,
        将该中心坐标的 1x1 方块选取加入到所有的 heatmap 中
        在 self.dict_dr 中记录好相应的方块分组信息
        返回添加的 series 最终 dr group id 以及该 series 在相应 df 中的 header (uuid)
        """
        def merge_dr_series_into_grp(dr_series: pd.Series, grp_id: int):
            """
            每次在一个 heatmap 上添加一个 dr, 实际上都要在所有的 heatmaps 上添加相同的 dr,
            因此每次添加的是一个 dr series
            本函数将这样一个 dr series 融入记录 dr 信息的总字典 self.dict_dr 中
            融入前不做任何判断(依赖函数外判断)
            1. 如果 grp_id 作为字典 key 不存在, 初始化 self.dict_dr[grp_id]
            2. 如果 grp_id 作为字典 key 存在, 但是相应的 val 为 `None` (用户手动清空一个 grp 组中的 rects 时, 会出现的情况), 同样初始化 self.dict_dr[grp_id]
            3. 引入 group fence 的概念, group fence 是一个与 dr 组中所有的 dr 相切的一个大矩形区域
               如果 dr series 中的 dr 中心落在 grp fence 的 fence +/- 1 的范围内, 将 dr 的范围 merge 到 dr grp 原始的 fence 范围之上
               如果 dr series 是 dr grp 的第一个 dr, 那么 series 中的 dr (都一样)就定义了这个新 dr group 的 fence 范围
            4. 将 series 中的每个 dr 的 user_data 设为 (grp_id: int, uuid : str)
            5. 为 series 中的 dr 按照 grp_id 分配颜色
            """
            if (grp_id not in self.dict_dr) or (self.dict_dr[grp_id] is None): # 在 grp_id 不存在时, 或则 self.dict_dr[grd_id] 为 None 时 (删除了所有某 dr 组中的 rects 后, 会出现这种情况, 组编号还存在, 但是其中没有任何 dr 了), 初始化这个 grp_id 对应的 ddict
                ddict = self.dict_dr[grp_id] = dict()
                ddict['grp dr df'] = pd.DataFrame() # 空 df, 后续用于 concatenate series
            else:
                ddict = self.dict_dr[grp_id]
            df_old = ddict['grp dr df']
            ddict['grp dr df'] = pd.concat([df_old, dr_series], axis = 1)
            tagDr = dr_series.iloc[0] # 取第一个 dr tag, 每个 series 中的所有的 dr 的位置必然都一样
            xmin, ymin, xmax, ymax = self.ensure_minmax_order(*dpg.get_value(tagDr))
            
            if 'fence' in ddict: # ddict 不是刚初始化的字典, 则会有 fence 这个 key
                xmin_old, ymin_old, xmax_old, ymax_old = ddict['fence'] # 新 drag rect 可能扩大 fence (但不可能缩小)
                xmin_new = xmin if xmin < xmin_old else xmin_old
                ymin_new = ymin if ymin < ymin_old else ymin_old
                xmax_new = xmax if xmax > xmax_old else xmax_old
                ymax_new = ymax if ymax > ymax_old else ymax_old
                ddict['fence'] = xmin_new, ymin_new, xmax_new, ymax_new
            else: # add the very first dr series in ddict, any dr's size defines the fence completely
                ddict['fence'] = xmin, ymin, xmax, ymax
            for tag in dr_series:
                dpg.set_item_user_data(tag, (grp_id, dr_series.name)) # group id and unique series id
                dpg.configure_item(tag, color=self.get_dr_color_in_group(grp_id))

        _, _, lst_allplts_mstr = self.get_all_maptags()
        """
        the default_value of dpg.add_drag_rect can be:
        (x1, y1) -> o---o
                    |   |
                    o---o <- (x2, y2)
        can also be:
                    o---o <- (x1, y1)
                    |   |
        (x2, y2) -> o---o
        what matters is the order of the two points
        x/y1 > x/y2 is always
        """

        dr_series = pd.Series([int(dpg.add_drag_rect(
            parent=p, default_value=(
                round(xmean_dr-sidex/2), # init x edge, or x1
                round(ymean_dr-sidey/2), # init y edge, or y1
                round(xmean_dr+sidex/2), # end x edge, or x2
                round(ymean_dr+sidey/2), # end y edge, or y2
                ), callback = self.sync_dr_series_update_mrh
            )) for p in lst_allplts_mstr], 
            index = lst_allplts_mstr,
            name= uuid.uuid4().hex,
            dtype= 'object' # 必须有这行, 这样 dr tag 才能被存储为 python int, 而不是 numpy.int64, 后者 dpg 不认. 若没有这行, pandas series 中的整数类型貌似被强制为 numpy.int64
            )
        
        create_first_table_cell = False
        add_to_existing_hist = False
        retake_empty_table_cell = False
        append_new_table_cell = False
        if not self.dict_dr: # if dr dict is empty
            grp_id_final = 0
            merge_dr_series_into_grp(dr_series, grp_id = grp_id_final)
            create_first_table_cell = True
        else:
            tagDr = dr_series.iloc[0] # 取第一个 dr tag, 每个 series 中的所有的 dr 的位置必然都一样
            x1, y1, x2, y2 = dpg.get_value(tagDr)
            xmean, ymean = (x1+x2)/2, (y1+y2)/2
            grp_id_final = None
            if not always_new_grp:
                for grp_id, ddict in self.dict_dr.items():
                    if ddict is not None: # skip empty groups
                        xmin, ymin, xmax, ymax = ddict['fence']
                        if (xmin-1<xmean<xmax+1) and (ymin-1<ymean<ymax+1):
                            merge_dr_series_into_grp(dr_series, grp_id)
                            grp_id_final = grp_id
                            add_to_existing_hist = True
                            break # 两个 fence 有 overlap 是完全可能的, 这时候随缘 merge 到第一个 fence 中
            if grp_id_final is None: # 如果新 dr 无法融入已存在的任何一个 dr 组的 fence 中, 则需要创建一个新的 dr grp
                for grp_id, val in self.dict_dr.items(): # 先看现存组中有没有空组可占用
                    if val is None: # 空 grp 组
                        merge_dr_series_into_grp(dr_series, grp_id)
                        grp_id_final = grp_id
                        retake_empty_table_cell = True
                        break
            if grp_id_final is None: # 若上一步并没有找到任何空 grp 组可以用新 series 占用
                grp_id_final = max(list(self.dict_dr))+1
                merge_dr_series_into_grp(dr_series, 
                                  grp_id_final)
                append_new_table_cell=True

        self.dq100.append((grp_id_final, dr_series.name))
        if update_hist_p:
            if create_first_table_cell:
                self.redraw_hist_sheet()
            elif add_to_existing_hist:
                self._update_one_hist(grp_id_final)
            elif retake_empty_table_cell:
                self.create_sp_for_existing_table_cell(grp_id_final)
            elif append_new_table_cell:
                ncols = dpg.get_value('hist sheet 列数')
                if grp_id_final%ncols ==0:
                    thisRow = dpg.add_table_row(parent = 'hist sheet table')
                else:
                    thisRow = dpg.get_item_parent(f'table cell-{grp_id_final-1}')
                with dpg.table_cell(parent=thisRow, tag = f'table cell-{grp_id_final}'):
                    self.create_sp_for_existing_table_cell(grp_id_final)
        return grp_id_final, dr_series.name
    def expunge_dr_series(self, grp_id, series_id, update_hist_p = True):
        """
        在所有热图和 self.dict_dr 中都删掉一个特定的 dr series
        它和 remove_dr_from_loc 的区别在于, 后者可以一次去除多个重叠的 dr
        """
        ddict = self.dict_dr[grp_id]
        df = ddict['grp dr df']
        for tag in df[series_id]:
            dpg.delete_item(tag)
        df.drop(series_id, axis=1, inplace=True)
        try:
            self.dq100.remove((grp_id, series_id))
        except ValueError:
            pass # 如果 dq100 中不存在待删除的条目, 也不要报错

        if df.size: # 如果 df 没被删空
            ddict['grp dr df'] = df
            self._update_grp_fence(grp_id)
            if update_hist_p:
                self._update_one_hist(grp_id)
        else:
            self.dict_dr[grp_id] = None
            if update_hist_p:
                dpg.delete_item(f'table cell-{grp_id}', children_only=True)
                winTag = f'window hist-{grp_id}'
                if dpg.does_item_exist(winTag):
                    dpg.delete_item(winTag)
    def remove_dr_from_loc(self, x_mouse: float, y_mouse: float, update_hist_p= True):
        for grp_id, ddict in self.dict_dr.items():
            if ddict is not None: # skip empty groups
                xminf, yminf, xmaxf, ymaxf = ddict['fence']
                if (xminf<x_mouse<xmaxf) and (yminf<y_mouse<ymaxf): # 粗筛, 首先判定鼠标点击在某个 dr 组的 fence 内
                    df = ddict['grp dr df']
                    dr_row = df.iloc[0,:] # 取第一行 drag rects, 代表了单张热图上的本组的所有 dr, 其他行(热图)上的 dr 都是同步的, 因此不用考虑
                    for drTag in dr_row: # 若鼠标点击在某个 dr 内, 则删除 dr 所在整列
                        xmindr, ymindr, xmaxdr, ymaxdr = self.ensure_minmax_order(*dpg.get_value(drTag))
                        if (xmindr<x_mouse<xmaxdr) and (ymindr<y_mouse<ymaxdr): # 细筛, 看鼠标是否点击在某个 dr 内
                            _, series_id = dpg.get_item_user_data(drTag)
                            self.expunge_dr_series(grp_id, series_id, update_hist_p=update_hist_p)

    def get_all_dr_tags(self):
        tag_list = []
        # fence_list = []
        for grp_id, ddict in self.dict_dr.items():
            if ddict is not None:
                tag_list += ddict['grp dr df'].values.flatten().tolist()
                # fence_list.append(ddict['fence'])
        return tag_list #, fence_list

    def clear_dr(self): # 不要用 get_all_dr_tags 来做, 因为 clear dr 的过程需要将相应的选取组设为 None
        for grp_id, ddict in self.dict_dr.items():
            if ddict is not None: # nonempty group
                for drTag in ddict['grp dr df'].values.flatten():
                    dpg.delete_item(drTag)
                self.dict_dr[grp_id] = None
                # clear standalone hist windows if any
                winTag = f'window hist-{grp_id}'
                if dpg.does_item_exist(winTag):
                    dpg.delete_item(winTag)
        self.dq100.clear()
        self.redraw_hist_sheet() # effectively clear all simple plots
    @deprecated
    def series_uuid_exists(self, series_uuid : str):
        uuid_lst_tot = []
        for ddict in self.dict_dr.values():
            if ddict is not None:
                df = ddict['grp dr df']
                uuid_lst_tot += list(df.columns)
        if series_uuid in uuid_lst_tot:
            return True
        else:
            return False
    def get_nonempty_grp_ids(self):
        grp_id_list = []
        for grp_id, ddict in self.dict_dr.items():
            if ddict is not None:
                grp_id_list.append(grp_id)
        return grp_id_list
    def _get_hist_series_from_grp(self, grp_id: int):
        """
        hist data is just ONE series (NOT two) of any data, nothing more, the yax of hist is just the data frequency
        this func returns empty list when the group is empty (group ddict is None)
        """
        if not self: # 如果 frame deck 中无帧(无采集), 则返回空列表, 因为此时若 dr 存在, 则按照逻辑, 相应的 sp 也必须存在, 但是其内容为空, 也就是空列表
            return []
        ddict = self.dict_dr[grp_id]
        df = ddict['grp dr df']
        drs_this_grp = df.iloc[0,:]
        frame_points_in_grp = set()
        for dr in drs_this_grp:
            xmin, ymin, xmax, ymax = [int(e) # need int, else e could be float, and cause error in range(e,e')
                                    for e in self.ensure_minmax_order(
                *self.ensure_1x1_area(*dpg.get_value(dr)))]
            xx, yy = np.meshgrid(range(xmin,xmax), range(ymin, ymax))
            pnts_in_dr = set([(x,y) for x,y in zip(xx.flatten(), yy.flatten())])
            frame_points_in_grp |= pnts_in_dr
        idarr_x, idarr_y = list(zip(*frame_points_in_grp))
        hist_series = []
        for frame in self.float_deck:
            selected_pixel_val_series = ZYLconversion(frame[
                idarr_y, # aha! the GOTCHA part! y shoud come first !
                idarr_x, 
                ])
            hist_series.append(selected_pixel_val_series.sum())
        return hist_series
    def _make_freq_series_from_grp(self, grp_id: int, binning: int = 1):
        """
        binning is one by default, maybe we add a field to change it in the future
        """
        binning = dpg.get_value('hist binning input')
        hist_series = self._get_hist_series_from_grp(grp_id)
        if not hist_series: # hist_series 为空只有一种可能: frame deck 为空. 此时 dr 组存在(否则根本不会调用本函数), 因此相应的 sp 也存在, 那么在 sp 中显示空数据 (主要目的还是为了在 sp 上显示选区编号的 overlay)
            freq_series, edge_min, edge_max = [], '', ''
        else:
            min_int, max_int = math.floor(min(hist_series)), math.floor(max(hist_series))
            nbins = (max_int-min_int)//binning + 1
            edge_min, edge_max = min_int, int(min_int + binning*nbins)
            """
            data *  *   *  *   *
            grid +---+---+---+---+
                |           |
            min_int     max_int

            `+`s are integer sites,
            in binning = 1 case, `+`s are bin edges to feed to np.histogram
            """
            freq_series, _ =np.histogram(hist_series, bins= np.linspace(edge_min, edge_max, nbins+1))
            freq_series = freq_series.astype(float)
        return freq_series, edge_min, edge_max, hist_series # hist_series aquisition can be expensive given thousands of frames, we return it so that it can be used in _update_one_hist together with frequency_series

    def _update_one_hist(self, grp_id: int):
        with self.lock:
            freq_series, edge_min, edge_max, hist_series = self._make_freq_series_from_grp(grp_id)
            dpg.set_value(f'sp-{grp_id}', freq_series)
            dpg.set_value(f'sp-xrange-{grp_id}', f'{edge_min}-{edge_max}')
            plotYax = f'yax hist-{grp_id}'
            if dpg.does_item_exist(plotYax):
                dpg.delete_item(plotYax, children_only=True)
                dpg.add_histogram_series(
                    hist_series, parent=plotYax,
                    # bins = len(freq_series), min_range = edge_min, max_range = edge_max,
                    )
                if hist_series: # 为预防用户在空 deck 情况下打开 hist plot, 这些需要实际 hist 数据的 plot 设置全部在 check 后再添加
                    dpg.configure_item(dpg.last_item(), bins = len(freq_series), min_range=edge_min, max_range = edge_max)
    def update_hist_sheet(self):
        with self.lock:
            for grp_id in self.get_nonempty_grp_ids():
                self._update_one_hist(grp_id)
    @staticmethod
    def _get_single_sp_width():
        width, height = dpg.get_item_rect_size('hist sheet window')
        single_sp_width = width / dpg.get_value('hist sheet 列数')*0.5
        return single_sp_width
    def set_sheet_sp_height_by_width(self):
        for grp_id in self.get_nonempty_grp_ids():
            dpg.configure_item(f'sp-{grp_id}', height= self._get_single_sp_width())
    def create_sp_for_existing_table_cell(self, grp_id : int):
        with self.lock:
            cellAlias = f'table cell-{grp_id}'
            spAlias = f'sp-{grp_id}'
            freq_series, edge_min, edge_max, _ = self._make_freq_series_from_grp(grp_id)
            dpg.add_simple_plot(parent = cellAlias, tag = spAlias,
                                width=-1, overlay=grp_id, 
                                default_value= freq_series, histogram=True)
            dpg.bind_item_theme(spAlias, self.tab_10_spThemes[grp_id % 10])
            dpg.configure_item(spAlias, height= self._get_single_sp_width()) # set sp height, hist sheet window resize handler will take care of the sp resize from then on
            dpg.add_text(f'{edge_min}-{edge_max}', parent = cellAlias,
                        tag = f'sp-xrange-{grp_id}')
            dpg.bind_item_handler_registry(dpg.last_item(), self.ihrTableCellText)
        
    def redraw_hist_sheet(self):
        """
        when to redraw:
        1. 清除所有 drag rects 时, 本命令等效于清空 hist sheet (因此应该放在 self.clear_dr() 最末)
        2. 批量添加 drag rects 阵列时, 不宜每增加一个 dr 就 update hist sheet 一次. 可以留待 dr 批量添加完毕后, 最后 redraw sheet
        3. 鼠标建立第一个 dr 时, redraw 可以帮助建立好所有的列
        """
        with self.lock:
            dpg.delete_item('hist sheet table', children_only=True) # clear old hist table before redraw
            ncols = dpg.get_value('hist sheet 列数')
            for icol in range(ncols):
                dpg.add_table_column(parent='hist sheet table', label = f'{icol+1}列')
            for grp_id, ddict in self.dict_dr.items():
                if grp_id%ncols == 0:
                    thisRow = dpg.add_table_row(parent='hist sheet table')
                with dpg.table_cell(parent=thisRow, tag= f'table cell-{grp_id}'):
                    if (ddict is not None): # leaves an empty table cell as place holder if ddict is None
                        self.create_sp_for_existing_table_cell(grp_id)
            self.set_sheet_sp_height_by_width()

def find_latest_camguiparams_json() ->MyPath:
    dpath_day = find_newest_daypath_in_save_tree(camgui_params_root)
    json_pattern = r'^CA([0-9]+)\.json$'
    def _camgui_json_sorter(fpath: MyPath):
        match = re.match(json_pattern, fpath.name)
        if match:
            return int(match.group(1))
        else:
            return -1
    lst_jsons = sorted(list(dpath_day.iterdir()), key= _camgui_json_sorter)
    if not lst_jsons:
        # push_log("异常: 最新日期的 camgui json 文件夹是空的", is_error=True)
        raise UserInterrupt('异常: 最新日期的 camgui json 文件夹是空的')
    fpath_newest_json = lst_jsons[-1]
    if not re.match(json_pattern, fpath_newest_json.name):
        # push_log("异常: camgui json save tree 最新日期文件夹中没有任何 json 文件", is_error=True)
        raise UserInterrupt('异常: camgui json save tree 最新日期文件夹中没有任何 json 文件')
    return fpath_newest_json

def _dummy_feed_awg(frame):
    pass
def _my_rand_frame(v=2304,h=4096, max=65535)-> np.ndarray:
    myarr = np.random.randint(0,max, size = v*h, dtype=np.uint16)
    return myarr.reshape((v,-1))


def ZYLconversion(frame: np.ndarray)->np.ndarray:
    """
    ZYL formula to infer photon counts
    """
    frame = (frame -200) * 0.1/0.9
    return frame

def return_time_consumption(func: callable):
    """
    decorator, 使无返回值的纯 command-like func 返回其执行时间 in ms
    """
    def wrapper(*args, **kwargs):
        beg = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        return (end - beg) *1e3
    return wrapper

feed_AWG = return_time_consumption(feed_AWG)

def st_workerf_flagged_do_all(
    cam: DCAM.DCAM.DCAMCamera,
    flag: threading.Event,
    frame_deck: FrameDeck,
    controller: DDSRampController, # type is DDSRampController, not hinted because it acts funny on macOS
    )-> None:
    """
    single-thread approach worker function which is flagged and does everythig:
    1. acquire frame from camera
    2. feed frame to AWG
    3. append frame to frame_deck
    4. plot frame
    """
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"] 
    awg_params = collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame :npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            # beg = time.time()
            time_consumption = feed_AWG(this_frame, controller, awg_params) # feed original uint16 format to AWG
            # end = time.time()
            push_log(f"重排前序计算耗时 {time_consumption:.3f} ms")
        frame_deck._append_save_plot(this_frame)
    cam.stop_acquisition()
    cam.set_trigger_mode("int")

def _dummy_st_workerf_flagged_do_all(
        flag: threading.Event, 
        frame_deck: FrameDeck):
    from fake_frames_imports import frame_list
    while flag.is_set():
        time.sleep(1)
        if frame_list:
            this_frame = frame_list.pop()
            frame_deck._append_save_plot(this_frame)
        else:
            break

#### objects for dual thread approach
_mt_dummy_remote_buffer = queue.Queue(maxsize=500) # 假相机 buffer, 双线程方案
_local_buffer = queue.SimpleQueue() # 双进程和双线程通用
def _workerf_dummy_remote_buffer_feeder(
        q: queue.Queue = _mt_dummy_remote_buffer)-> None:
    """
    假相机 buffer 的 filler, 由假触发 checkbox 控制是否向假相机 buffer 中放 frame
    """
    from fake_frames_imports import frame_list
    frame_list_ = copy.deepcopy(frame_list)
    del frame_list
    while True:
        time.sleep(1) # simulate snap rate
        if dpg.get_value("假触发"):
            if frame_list_:
                this_frame = frame_list_.pop()
                q.put(this_frame)
            else:
                push_log("已向假相机 mt buffer 发送 500 帧", is_good=True)
                break
def _dummy_mt_producerf_polling_do_snag_rearrange_deposit(
        flag: threading.Event,
        q: queue.Queue = _mt_dummy_remote_buffer,
        qlocal: queue.SimpleQueue = _local_buffer,
        )->None:
    """
    假 producer
    从假相机 buffer 中取 frame, 放入 local buffer
    polling a flag. flag clear 时, 投毒, 停止循环
    """
    while flag.is_set():
        try:
            this_frame: npt.NDArray[np.uint16] = q.get(timeout=0.2)
        except queue.Empty:
            continue
        time.sleep(0.01) # 模拟重排耗时
        qlocal.put(this_frame)
    qlocal.put(None) # poison pill

def consumerf_local_buffer(
        frame_deck: FrameDeck,
        qlocal: queue.SimpleQueue = _local_buffer, 
        )->None:
    """
    consumer (双线程和双进程通用)
    从 local buffer 中取 frame, 然后:
    1. 放入 frame deck
    2. 绘图
    3. 保存帧
    """
    while True:
        this_frame = qlocal.get()
        if this_frame is None: # poison pill
            break # looping worker killed
        frame_deck._append_save_plot(this_frame)

def mt_producerf_polling_do_snag_rearrange_deposit(
        cam: DCAM.DCAM.DCAMCamera,
        flag: threading.Event,
        controller : DDSRampController, # type is DDSRampController, not hinted because it acts funny on macOS
        local_buffer: queue.SimpleQueue = _local_buffer,
        )->None:
    """
    双线程 producer,
    从 camera 中取 frame, 放入 local buffer
    polling a flag, flag clear 时, 投毒, 终止
    """
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes=100)
    awg_is_on = dpg.get_item_user_data("AWG toggle")["is on"] 
    awg_params = collect_awg_params()
    while flag.is_set():
        try:
            cam.wait_for_frame(timeout=0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame: npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            time_consumption = feed_AWG(this_frame, controller, awg_params)
            push_log(f"重排前序计算耗时 {time_consumption:.3f} ms")
        local_buffer.put(this_frame)
    cam.stop_acquisition()
    cam.set_trigger_mode("int")
    local_buffer.put(None) # poison pill    

### dual processes approach 需要的 objects:
def _mp_workerf_dummy_remote_buffer_feeder(
        q: multiprocessing.Queue)-> None:
    """
    假相机 buffer 的 feeder, 这里的假 buffer 是一个 multiprocessing.Queue,
    由主线程填充, 由假触发 checkbox 控制是否向假 buffer 中放 frame
    """
    from fake_frames_imports import frame_list
    frame_list_ = copy.deepcopy(frame_list)
    del frame_list
    while True:
        time.sleep(1) # simulate snap rate
        if dpg.get_value("假触发"):
            if frame_list_:
                this_frame = frame_list_.pop()
                q.put(this_frame)
                # print("fed frame")
            else:
                push_log("已向假相机 mp buffer 发送 500 帧", is_good=True)
                break

def _dummy_mp_producerf_polling_do_snag_rearrange_send(
        conn_sig: multiprocessing.connection.Connection,
        conn_data: multiprocessing.connection.Connection,
        conn_debug: multiprocessing.connection.Connection,
        q: multiprocessing.Queue
        ):
    # conn_debug.send("inside")
    while not conn_sig.poll():
        # conn_debug.send("looping")
        try:
            this_frame: npt.NDArray[np.uint16] = q.get(timeout=0.2)
            # conn_debug.send("produced frame")
        except queue.Empty:
            continue
        time.sleep(0.01) # 模拟重排耗时
        conn_data.send(this_frame)
    conn_sig.close()
    conn_data.send(None) # poison pill
    conn_data.close()
    conn_debug.close()

def mp_producerf_polling_do_snag_rearrange_send(
        conn_sig: multiprocessing.connection.Connection,
        conn_data: multiprocessing.connection.Connection,
        cam_params: Sequence[float],
        awg_is_on: bool, # 这个 bool 不能在放 body 中获取, 因为 body 是在新进程中运行, 而在新进程中, main guard 阻止了这个 producer 接触一切 gui 相关代码
        awg_params: Sequence # 无论 awg 是否开启都必须加上, 因为 multiprocessing.Process 的 args 参数是固定的
        ):
    """
    双进程 producer, 运行于从进程
    打开 cam, 设置 camera, 打开 awg (如果 gui 开了)
    从 camera 中取 frame, 重排 (如果 gui 开了), 然后放入 data pipe
    polling signal pipe, 当收到 signal 时, 关闭 cam, 关闭 awg (如果 gui 开了), 投毒
    """
    if awg_is_on:
        raw_card, controller = gui_open_awg()
    exposure, hstart, hend, vstart, vend, hbin, vbin = cam_params
    cam = DCAM.DCAMCamera() # 无论是否需要 awg, cam obj 是一定需要的
    cam.open()
    cam.set_exposure(exposure)
    cam.set_roi(hstart, hend, vstart, vend, hbin, vbin)
    cam.set_trigger_mode("ext")
    cam.start_acquisition(mode="sequence", nframes = 100)
    conn_sig.send('cam all set in the alternative session')
    while not conn_sig.poll():
        try:
            cam.wait_for_frame(timeout = 0.2)
        except DCAM.DCAMTimeoutError:
            continue
        this_frame: npt.NDArray[np.uint16] = cam.read_oldest_image()
        if awg_is_on:
            time_consumption = feed_AWG(this_frame, controller, awg_params)
            conn_sig.send(time_consumption) # send time consumption to mp_passerf
        conn_data.send(this_frame)
    if awg_is_on:
        raw_card.close()
        controller = None # for possible garbage collection
    cam.close()
    conn_sig.close()
    conn_data.send(None) # poison pill
    conn_data.close()

def mp_passerf(
        conn_data: multiprocessing.connection.Connection,
        conn_sig: multiprocessing.connection.Connection,
        awg_is_on: bool,
        q: queue.SimpleQueue = _local_buffer):
    while True:
        this_frame = conn_data.recv()
        if awg_is_on:
            time_consumption = conn_sig.recv() # receive time consumption from mp_producerf_polling_do_snag_rearrange_send
            push_log(f"重排前序计算耗时 {time_consumption:.3f} ms")
        q.put(this_frame)
        if this_frame is None:
            conn_data.close()
            break

def _log(sender, app_data, user_data):
    """
    helper function from demo.py. 可以作为还没写好的 callback 的 placeholder，
    coding 时用来查看 callback 的所有三个 argument：
    - sender：the id of the UI item that submitted teh callback
    - app_data: occasionally UI items will send their own data (e.g. file dialog)
    - user_data: any python object you want to send to the function
    (quoted from dpg online doc)
    """
    print(f"sender: {sender}, \t app_data: {app_data}, \t user_data: {user_data}")

def rgb_opposite(r, g, b):
    """
    给出某 rgb 相对最大对比度颜色（HSL approach）。@GPT
    """
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255) # convert to HSL
    h = (h + 0.5) % 1.0 # Rotate hue by 180° (opposite color)
    l = 1.0 - l # invert lightness
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s) # Convert back to RGB
    return int(r2*255), int(g2*255), int(b2*255)

def gui_open_awg():
    raw_card = spcm.Card(card_type = spcm.SPCM_TYPE_AO)
    raw_card.open()
    controller = DDSRampController(raw_card)
    return raw_card, controller

def collect_awg_params() -> tuple:
    x1, y1, *_ = dpg.get_value("x1 y1")
    x2, y2, *_ = dpg.get_value("x2 y2")
    x3, y3, *_ = dpg.get_value("x3 y3")
    nx, ny, *_ = dpg.get_value("nx ny")
    x0, y0, *_ = dpg.get_value("x0 y0")
    rec_x, rec_y, *_ = dpg.get_value("rec_x rec_y")
    count_threshold = dpg.get_value("count_threshold")
    n_packed = dpg.get_value("n_packed")
    start_frequency_on_row, start_frequency_on_col, *_ = dpg.get_value("start_frequency_on_row(col)")
    start_frequency_on_row*= 1e6
    start_frequency_on_col*= 1e6
    end_frequency_on_row, end_frequency_on_col, *_ = dpg.get_value("end_frequency_on_row(col)")
    end_frequency_on_row*=1e6
    end_frequency_on_col*=1e6
    start_site_on_row, start_site_on_col, *_ = dpg.get_value("start_site_on_row(col)")
    end_site_on_row, end_site_on_col, *_ = dpg.get_value("end_site_on_row(col)")
    num_segments = dpg.get_value("num_segments")
    power_ramp_time = dpg.get_value("power_ramp_time (ms)")
    power_ramp_time*=1e-3
    move_time = dpg.get_value("move_time (ms)")
    move_time *= 1e-3
    percentage_total_power_for_list = dpg.get_value("percentage_total_power_for_list")
    ramp_type = dpg.get_value("ramp_type")
    user_tgt_arr_input: str = dpg.get_value("target array binary text input")
    lines = user_tgt_arr_input.replace(" ", "").strip().splitlines()
    tgt2darr = np.array([[int(ch) for ch in line] for line in lines if line != ""], dtype=int)
    return (x1,y1, x2, y2, x3, y3, nx, ny, x0, y0, rec_x, rec_y, count_threshold,
            n_packed, start_frequency_on_row, start_frequency_on_col,
            end_frequency_on_row, end_frequency_on_col,
            start_site_on_row, start_site_on_col,
            end_site_on_row, end_site_on_col,
            num_segments, power_ramp_time, move_time,
            percentage_total_power_for_list, ramp_type, tgt2darr)


_bullets = cycle(["-", "*", "+", "•", "°"])
def _push_log(msg:str, *, 
             is_error: bool=False,
             is_good: bool=False,
             is_warning = False):
    """
    将 message 显示在 log window 中
    仅仅在 context 创建完毕后有效
    """
    tagWin = "log window"
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S.") + f"{now.microsecond//1000:03d}"
    if is_error:
        color = (255,0,0)
    elif is_good:
        color = (0,255,0)
    elif is_warning:
        color = (255,222,33)
    else:
        color = None
    dpg.add_text(next(_bullets)+timestamp+"\n"+msg, 
                parent= tagWin, 
                color = color,
                wrap= 150)
    
    win_children: Dict[int, List[int]] = dpg.get_item_children(tagWin)
    lst_tags_msgs = win_children[1]
    if len(lst_tags_msgs)>100: # log 最多 100 条
        oldestTxt = lst_tags_msgs.pop(0)
        dpg.delete_item(oldestTxt)

    dpg.set_y_scroll(tagWin, dpg.get_y_scroll_max(tagWin)+20 # the +20 is necessary because IDK why the window does not scroll to the very bottom, there's a ~20 margin, strange. 
                    )

def push_log(*args, **kwargs):
    """
    context 创建过程中, 就可以预先设置在 camgui 启动后显示的异常
    """
    if dpg.is_dearpygui_running():
        _push_log(*args, **kwargs)
    else:
        dpg.set_frame_callback(3, lambda: _push_log(*args, **kwargs))

def push_exception(user_msg: str=""):
    """
    在 camgui log window 中显示 traceback 的 exception
    """
    # traceback.print_exc() # for REPL review
    push_log(user_msg 
             + "\n" 
             + traceback.format_exc(), is_error=True)

CamguiParams = namedtuple(typename='CamguiParams',
                          field_names=[ # the point of namedtuple is to fix these keys 
                              '并发方式',
                              'cam面板参数',
                              'awg面板参数',
                              'Camgui版本',
                              ],
                              defaults = [camgui_ver])
def save_camgui_json_to_savetree():
    panel_params = CamguiParams( # 先把能直接 dpg.get_value 的 string tag 排好, 如果 tag 有拼写错误, 接下来在 dpg.get_value 时就会报错
        并发方式 = {
            '无并发: 单线程采集重排绘图保存' : None,
            '双线程: 采集重排 & 绘图保存' : None,
            '双进程: 采集重排 & 绘图保存' : None,
        },
        cam面板参数 = {
            'exposure field' : None,
            'h start & h length:' : None,
            'v start & v length:' : None,
            'h binning & v binning' : None,
        },
        awg面板参数 = {
            'awg is on' : dpg.get_item_user_data('AWG toggle')['is on'],
            'x1 y1' : None,
            'x2 y2' : None,
            'x3 y3' : None,
            'nx ny' : None,
            'x0 y0' : None,
            'rec_x rec_y' : None,
            'count_threshold' : None,
            'n_packed' : None,
            "start_frequency_on_row(col)" : None,
            "end_frequency_on_row(col)" : None,
            "start_site_on_row(col)" : None,
            "end_site_on_row(col)" : None,
            'num_segments' : None,
            'power_ramp_time (ms)' : None,
            'move_time (ms)' : None,
            'percentage_total_power_for_list' : None,
            'ramp_type' : None,
            'target array binary text input' : None,
            })
    for key in panel_params.并发方式:
        panel_params.并发方式[key] = dpg.get_value(key)
    for key in panel_params.cam面板参数:
        panel_params.cam面板参数[key] = dpg.get_value(key)
    for key in panel_params.awg面板参数:
        if key != 'awg is on':
            panel_params.awg面板参数[key] = dpg.get_value(key)
    dpath_day = _mk_save_tree_from_root_to_day(camgui_params_root)
    extra_confirm = False
    if dpath_day.exists():
        try:
            fpath_newest_json = find_latest_camguiparams_json()
            json_num_latest = int((fpath_newest_json.name[2:])[:-5]) #掐头去尾, 从 e.g. CA100.json 得到 100
            new_str_json = 'CA' + str(json_num_latest + 1) + '.json'
        except UserInterrupt:
            push_exception('保存 camgui json 文件时发现异常')
            new_str_json = 'CA1.json'
            extra_confirm = True
    else:
        dpath_day.mkdir(parents=True)
        new_str_json = 'CA1.json'
    fpath = dpath_day / new_str_json
    with open(fpath, 'w') as f:
        json.dump(panel_params._asdict(), f, 
                  indent = 2, # @GPT more human-readable
                  ensure_ascii=False # to save chinese
                  )
    if extra_confirm:
        push_log('虽然有异常, 但是 camgui json 文件夹依然创建成功', is_good =True)
    return new_str_json