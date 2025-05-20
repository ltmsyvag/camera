#%%
from camguihelper import CamguiParams
import json
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
            # 'awg is on' : dpg.get_item_user_data('AWG toggle')['is on'],
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

with open('testfile.json', 'w') as f:
    json.dump(panel_params._asdict(), f, 
                indent = 2 # @GPT more human-readable
                )
#%%

mydict = {'a' : 100}

val, = mydict.values()
val
type(mydict) is dict
#%% my
import json
jsonpath = '/Users/haiteng/Documents/labwork/camera/session_data_root/camgui_params/2025/五月/20/CA10.json'
with open(jsonpath, 'r') as f:
    data = json.load(f)
#%%

from camguihelper import CamguiParams
# print(CamguiParams.Camgui版本)