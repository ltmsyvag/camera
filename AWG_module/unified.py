#%%
from .image_to_atom_array import image_process
from .rearrangement_method_zylcopy import main
from .coordinate_to_frequency import convert_coordinate_to_frequency
from .no_with_func import rearrange
import spcm
# import tifffile

# image = tifffile.imread("frame.tif")

raw_card = spcm.Card(card_type=spcm.SPCM_TYPE_AO)
raw_card.open()
# controller = DDSRampController(raw_card)

def feed_AWG(frame, controller):
    x1=40 #基矢起点x坐标
    y1=28 #基矢起点y坐标
    x2=128 #x方向基矢x坐标
    y2=30 #x方向基矢y坐标
    x3=37 #y方向基矢x坐标
    y3=116 #y方向基矢y坐标
    nx=16 #阵列x方向尺寸
    ny=16 #阵列y方向尺寸
    x0=x1-1 #选择起点
    y0=y1-1 
    rec_x=3 #每个点位选择统计光子数的mask大小
    rec_y=3
    count_threshold = 50 #int 判断是否有光子的阈值
    _, atom_array = image_process(frame, nx, ny, x0, y0, x1, y1, x2, y2, x3, y3, rec_x, rec_y, count_threshold)
    complete_moves = main(atom_array)

    start_frequency_on_row = 90e6 #floor,行方向的起始频率
    start_frequency_on_col  = 90e6 #floor,列方向的起始频率
    end_frequency_on_row = 110e6 #floor,行方向的终止频率
    end_frequency_on_col = 110e6 #floor,行方向的终止频率
    start_site_on_row = 0 #int,行方向的原子起始坐标
    start_site_on_col = 0 #int,列方向的原子起始坐标
    end_site_on_row = 15 #int,行方向的原子终止坐标
    end_site_on_col = 15 #int,列方向的原子终止坐标
    tuple_of_4 = convert_coordinate_to_frequency(start_frequency_on_row, start_frequency_on_col,end_frequency_on_row, end_frequency_on_col, start_site_on_row, start_site_on_col, end_site_on_row, end_site_on_col,complete_moves)

    num_segments = 30 #int,决定了s曲线ramp的平滑成都
    power_ramp_time = 1#floor, 功率ramp的时间
    move_time = 1#floor, 频率ramp的时间，也就是单个光镊移动的时间
    percentage_total_power_for_list = 0.01#floor, 送入aod每个轴的最大功率，是一个百分数，代表最终上升到awg设定最大电平的多少
    ramp_type = 'cosine' #string,决定了扫频的曲线形式
    rearrange(controller, num_segments,tuple_of_4,power_ramp_time,move_time,percentage_total_power_for_list,ramp_type)