#%%
from .image_to_atom_array import image_process
from .rearrangement_method_no_reservior_zyl_v4 import main
from .coordinate_to_frequency import convert_coordinate_to_frequency
from .no_with_func_test import rearrange_test
import numpy as np
# import spcm
# import tifffile

# image = tifffile.imread("frame.tif")

# raw_card = spcm.Card(card_type=spcm.SPCM_TYPE_AO)
# raw_card.open()
# controller = DDSRampController(raw_card)

def feed_AWG(frame, controller, awg_params: tuple)->None:
    (x1,y1, x2, y2, x3, y3, nx, ny, x0, y0, rec_x, rec_y, count_threshold,
            n_packed, start_frequency_on_row, start_frequency_on_col,
            end_frequency_on_row, end_frequency_on_col,
            start_site_on_row, start_site_on_col,
            end_site_on_row, end_site_on_col,
            num_segments, power_ramp_time, move_time,
            percentage_total_power_for_list, ramp_type, target_array) = awg_params
    # x1=36 #基矢起点x坐标
    # y1=23 #基矢起点y坐标
    # x2=124 #x方向基矢x坐标
    # y2=25 #x方向基矢y坐标
    # x3=34 #y方向基矢x坐标
    # y3=112 #y方向基矢y坐标
    # nx=16 #阵列x方向尺寸
    # ny=16 #阵列y方向尺寸
    # x0=x1-2 #选择起点
    # y0=y1-2 
    # rec_x=4 #每个点位选择统计光子数的mask大小
    # rec_y=4
    # count_threshold = 30 #int 判断是否有光子的阈值
    _, atom_array = image_process(frame, nx, ny, x0, y0, x1, y1, x2, y2, x3, y3, rec_x, rec_y, count_threshold)


    # target_array = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    #                          [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])  #目标矩阵
    # n_packed = 3 #int,决定了每次移动的原子数


    complete_moves = main(atom_array , target_array, n_packed)

    # start_frequency_on_row = 90.8e6 #floor,行方向的起始频率，即第一行对应的频率
    # start_frequency_on_col  = 111.4e6 #floor,列方向的起始频率
    # end_frequency_on_row = 111.3e6 #floor,行方向的终止频率
    # end_frequency_on_col = 90.8e6 #floor,行方向的终止频率
    # start_site_on_row = 0 #int,行方向的原子起始坐标
    # start_site_on_col = 0 #int,列方向的原子起始坐标
    # end_site_on_row = 15 #int,行方向的原子终止坐标
    # end_site_on_col = 15 #int,列方向的原子终止坐标
    tuple_of_4 = convert_coordinate_to_frequency(start_frequency_on_row, start_frequency_on_col,end_frequency_on_row, end_frequency_on_col, start_site_on_row, start_site_on_col, end_site_on_row, end_site_on_col,complete_moves)

    # num_segments = 16 #int,决定了s曲线ramp的平滑程度
    # power_ramp_time = 40e-4#floor, 功率ramp的时间
    # move_time = 20e-4#floor, 频率ramp的速度，也就是单个光镊移动的速度
    # percentage_total_power_for_list = 0.5#floor, 送入aod每个轴的最大功率，是一个百分数，代表最终上升到awg设定最大电平的多少
    # ramp_type = '5th-order' #string,决定了扫频的曲线形式
    rearrange_test(controller, num_segments,tuple_of_4,power_ramp_time,move_time,percentage_total_power_for_list,ramp_type)