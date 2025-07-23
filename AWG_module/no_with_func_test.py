"""
Spectrum AWG control by ZYL 2025.3.4
"""
import spcm
from spcm import units
import psutil
import os
import numpy as np
# import matplotlib.pyplot as plt
import random
# import time
# Set the highest process priority to the Python process, to enable highest possible command streaming
p = psutil.Process(os.getpid())
p.nice(psutil.REALTIME_PRIORITY_CLASS)


class DDSRampController:
    """Changing frequency Class """
    def __init__(self,card):
        self.card = card
        self._setup_base_config()
        self._ext_trigger_config()
        self._dds_config()
        self._xio_config()
        self.card.write_setup()
        self.card.start(spcm.M2CMD_CARD_ENABLETRIGGER)



    def _setup_base_config(self):
        """basic hardware config"""
        self.card.card_mode(spcm.SPC_REP_STD_DDS)
        self.channels = spcm.Channels(self.card)
        self.channels.enable(True)
        self.channels.amp(0.25 * units.V)
        self.card.write_setup()



    def _ext_trigger_config(self,
                          level=1.5 * units.V,
                          mode=spcm.SPC_TM_POS):
        """configure external trigger
        Args:
        """
        self.trigger = spcm.Trigger(self.card)
        self.trigger.or_mask(spcm.SPC_TMASK_EXT0)
        self.trigger.ext0_mode(mode)
        self.trigger.ext0_level0(level)
        self.trigger.ext0_coupling(spcm.COUPLING_DC)


    def _dds_config(self):
        # Setup DDS functionality
        self.dds = spcm.DDSCommandQueue(self.card, channels=self.channels)
        self.dds.reset()
        self.dds.data_transfer_mode(spcm.SPCM_DDS_DTM_DMA)
        self.dds.cores_on_channel(1,
                             spcm.SPCM_DDS_CORE20)  # Fixed core 20 as the single frequency
        self.dds.trg_src(spcm.SPCM_DDS_TRG_SRC_TIMER)
        self.dds.mode = self.dds.WRITE_MODE.WAIT_IF_FULL


    def _xio_config(self):
        # Activate the xio dds mode
        self.multi_ios = spcm.MultiPurposeIOs(self.card)
        self.multi_ios[0].x_mode(spcm.SPCM_XMODE_DDS)
        self.card.write_setup()
        self.dds.x_mode(0, spcm.SPCM_DDS_XMODE_MANUAL)




    def s_curve(self,t):
        """S形曲线函数: 6t⁵ - 15t⁴ + 10t³"""
        return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3


    def s_curve_integral(self,t):
        """S形曲线函数的积分: t⁶ - 3t⁵ + 2.5t⁴"""
        return t ** 6 - 3 * t ** 5 + 2.5 * t ** 4


    def generate_fm_waveform(self,
            move_time=1.0,  # 总持续时间(秒)
            rise_time=0.2,  # 幅度上升时间(秒)
            fall_time=0.2,  # 幅度下降时间(秒)
            sampling_rate=100,  # 采样率(Hz)
            base_freq=89e6,  # 起始频率(Hz)
            max_freq=95e6,  # 最大频率(Hz)
            max_amplitude=1  # 最大幅度
    ):
        """生成带S形幅度变化的S形扫频波形"""
        # 计算各阶段样本数
        duration = move_time + rise_time + fall_time
        total_samples = int(round(sampling_rate * duration))
        rise_samples = int(sampling_rate * rise_time)
        fall_samples = int(sampling_rate * fall_time)
        steady_samples = int(sampling_rate * move_time)

        # 确保时间参数合法
        if steady_samples < 0:
            raise ValueError("上升时间+下降时间不能超过总持续时间")

        # 定义扫描阶段的起始和结束索引（关键修复：确保始终有定义）
        sweep_start = rise_samples
        sweep_end = sweep_start + steady_samples  # 无论steady_samples是否为0，均有定义

        # 生成时间轴
        t = np.linspace(0, duration, total_samples, endpoint=False)



        # 频率轮廓（修复：直接设置下降阶段频率为max_freq）
        freq_profile = np.ones(total_samples) * base_freq
        # 稳定阶段：频率从base_freq扫到max_freq（S形）
        if steady_samples > 0:
            sweep_t = np.linspace(0, 1, steady_samples)
            freq_profile[sweep_start:sweep_end] = base_freq + (max_freq - base_freq) * self.s_curve(sweep_t)
        # 下降阶段：频率保持max_freq（直接赋值，避免冗余计算）
        freq_profile[sweep_end:] = max_freq


        # 幅度轮廓（S形上升和下降）
        amplitude_profile = np.ones(total_samples) * max_amplitude
        # 上升阶段：从0到max_amplitude（S形）
        if rise_samples > 0:
            rise_t = np.linspace(0, 1, rise_samples)
            amplitude_profile[:rise_samples] = max_amplitude * self.s_curve(rise_t)
        # 下降阶段：从max_amplitude到0（S形）
        if fall_samples > 0:
            fall_start = total_samples - fall_samples
            fall_t = np.linspace(0, 1, fall_samples)
            amplitude_profile[fall_start:] = max_amplitude * (1 - self.s_curve(fall_t))



        #delta_phase = 2 * np.pi * freq_profile / sampling_rate
        #phase = np.cumsum(delta_phase)

        # 生成最终波形
        #waveform = amplitude_profile * np.sin(phase)
        waveform = 0  #实际波形在这里不重要，可以忽略

        return t, waveform, freq_profile, amplitude_profile
    
    
    
    # A generator function for s-shaped ramps
    def generate_function(self, t, parameters, num_segments):
        if parameters["ramp_type"] == 'cosine':
            # cosine
            y = (0.5 - 0.5 * np.cos(np.pi * t))
        elif parameters["ramp_type"] == 'square':
            # square
            a = np.concatenate([(0,), np.ones(((num_segments + 1) // 2,)), -np.ones(((num_segments + 1) // 2,))])
            v = np.cumsum(a) * parameters["time_s"] / num_segments
            y = np.cumsum(v) * parameters["time_s"] / num_segments
        elif parameters["ramp_type"] == '3rd-order':
            # 3rd order
            b = 4 * np.concatenate([(0,), np.ones(((num_segments + 1) // 4,)), -np.ones(((num_segments + 1) // 2,)),
                                    np.ones(((num_segments + 1) // 4,))])
            a = np.cumsum(b) * parameters["time_s"] / num_segments
            v = np.cumsum(a) * parameters["time_s"] / num_segments
            y = np.cumsum(v) * parameters["time_s"] / num_segments
        elif parameters["ramp_type"] == '5th-order':
            y = (6*t**5 - 15*t**4 + 10*t**3)
        y = parameters["startFreq_Hz"] + y / y[-1] * (parameters["endFreq_Hz"] - parameters["startFreq_Hz"])
        return y

    def calculate_slope(self, t, y):
        # Slopes along the lines
        t_diff = np.diff(t)
        y_diff = np.diff(y)
        return np.divide(y_diff, t_diff)

    def ramp_slope_generate(self, num_segments, start_frequency_list, end_frequency_list, move_time, power_ramp_time ,ramp_type):
        amp_profiles_all = np.zeros((len(start_frequency_list), num_segments))
        amp_profiles_ori = np.zeros(num_segments)
        fre_profiles_all = np.zeros((len(start_frequency_list), num_segments))
        for i in range(len(start_frequency_list)):
            t, waveform, freq_profile, amplitude_profile = self.generate_fm_waveform(
            move_time=move_time,  # 总持续时间(秒)
            rise_time=power_ramp_time,  # 幅度上升时间(秒)
            fall_time=power_ramp_time,  # 幅度下降时间(秒)
            sampling_rate=num_segments/(move_time+2*power_ramp_time),  # 采样率(Hz)
            base_freq=start_frequency_list[i],  # 起始频率(Hz)
            max_freq=end_frequency_list[i],  # 终止频率(Hz)
            max_amplitude=1  # 最大幅度
            )
            amp_profiles_ori[:] = amplitude_profile
            freq_profile_norm = (freq_profile/1e6 - 101.4)/10.39
            amplitude_profile = amplitude_profile*(0.8560/(0.0080*freq_profile_norm**6-0.0028*freq_profile_norm**5-0.0767*freq_profile_norm**4+0.0200*freq_profile_norm**3+0.1707*freq_profile_norm**2-0.0466*freq_profile_norm**1+0.7926))**1.1 #x轴AOD的校正
            amp_profiles_all[i,:]=amplitude_profile
            fre_profiles_all[i,:]=freq_profile
        self.amp_profiles_ori = amp_profiles_ori
        self.amp_profiles_all = amp_profiles_all
        self.fre_profiles_all = fre_profiles_all



    def execute_ramp(self, num_segments, single_frequency ,start_frequency_list, end_frequency_list, power_ramp_time ,move_time, percentage_total_power_for_list):
        y_fre_norm=(single_frequency/1e6-100.8)/10.39  #将y轴AOD的频率正则化，送入功率校正曲线中
        y_amp_correction = (1.2107/(0.0044*y_fre_norm**6-0.0016*y_fre_norm**5-0.0641*y_fre_norm**4+0.0060*y_fre_norm**3+0.1461*y_fre_norm**2-0.0013*y_fre_norm**1+1.1629))**1.9
        number_of_frequencies = len(start_frequency_list)
        random_phase_list = [random.randint(0,360)for i in range(number_of_frequencies)] #generate the random phase list for different dds core
        period_s = (move_time+2*power_ramp_time)/num_segments
        self.dds.trg_timer(period_s)
        self.dds.write_to_card()


        """set single fre AOD"""
        self.dds[20].amp(0.4 * y_amp_correction)
        self.dds[20].freq(single_frequency)
        for i in range(number_of_frequencies):
            self.dds[i].phase(random_phase_list[i])
        self.dds.exec_at_trg()
        self.dds.write_to_card()
        
        
        """set multiple frequencies AOD"""
        
        for j in range(num_segments):
            for i in range(number_of_frequencies):
                self.dds.amp(i, percentage_total_power_for_list * self.amp_profiles_all[i][j])
                self.dds.freq(i, self.fre_profiles_all[i][j])
            self.dds.exec_at_trg()
        for i in range(number_of_frequencies):
            self.dds.amp(i,0)
        self.dds[20].amp(0)
        self.dds.exec_at_trg()
        self.dds.write_to_card()



    def complete_rearrange(self, num_segments, row_or_col_list, single_frequency_list, start_frequency_table, end_frequency_table, power_ramp_time, move_time, percentage_total_power_for_list, ramp_type):

        for i in range(len(row_or_col_list)):
            if row_or_col_list[i]: #True means row rearrangement
                self.dds.x_manual_output(0x0)  # keep low level
                self.dds.trg_timer(1e-6)
                self.dds.exec_at_trg()
            else:
                self.dds.x_manual_output(spcm.SPCM_DDS_X0)  # keep high level, control the RF switch to change
                self.dds.trg_timer(1e-6)
                self.dds.exec_at_trg()
            self.ramp_slope_generate(num_segments = num_segments, start_frequency_list = start_frequency_table[i], end_frequency_list = end_frequency_table[i], move_time = move_time, power_ramp_time=power_ramp_time,ramp_type = ramp_type)
            self.execute_ramp(num_segments=num_segments, single_frequency=single_frequency_list[i],
                                start_frequency_list=start_frequency_table[i],
                                end_frequency_list=end_frequency_table[i], power_ramp_time=power_ramp_time,
                                move_time=move_time, percentage_total_power_for_list=percentage_total_power_for_list)


    def run_the_procedure(self, how_many_times, num_segments, row_or_col_list, single_frequency_list, start_frequency_table, end_frequency_table, power_ramp_time, move_time, percentage_total_power_for_list, ramp_type):
        if how_many_times == 0: #first run, some configuration should be made

            self.dds.trg_src(spcm.SPCM_DDS_TRG_SRC_TIMER)
            self.dds.write_to_card()
            self.card.cmd(spcm.M2CMD_CARD_FORCETRIGGER)
            self.complete_rearrange(num_segments=num_segments, row_or_col_list=row_or_col_list,
                                    single_frequency_list=single_frequency_list,
                                    start_frequency_table=start_frequency_table,
                                    end_frequency_table=end_frequency_table, power_ramp_time=power_ramp_time,
                                    move_time=move_time,
                                    percentage_total_power_for_list=percentage_total_power_for_list,
                                    ramp_type=ramp_type)
            self.card.cmd(spcm.M2CMD_CARD_FORCETRIGGER)
            self.dds.trg_src(spcm.SPCM_DDS_TRG_SRC_CARD)
            self.dds.write_to_card()
            self.dds.exec_now()
            self.dds.exec_at_trg()

        else:

            self.dds.trg_src(spcm.SPCM_DDS_TRG_SRC_TIMER)
            self.dds.write_to_card()
            self.card.cmd(spcm.M2CMD_CARD_FORCETRIGGER)
            self.complete_rearrange(num_segments=num_segments, row_or_col_list=row_or_col_list,
                                    single_frequency_list=single_frequency_list,
                                    start_frequency_table=start_frequency_table,
                                    end_frequency_table=end_frequency_table, power_ramp_time=power_ramp_time,
                                    move_time=move_time,
                                    percentage_total_power_for_list=percentage_total_power_for_list,
                                    ramp_type=ramp_type)
            self.card.cmd(spcm.M2CMD_CARD_FORCETRIGGER)
            self.dds.trg_src(spcm.SPCM_DDS_TRG_SRC_CARD)
            self.dds.write_to_card()
            self.dds.exec_now()
            self.dds.exec_at_trg()




# with spcm.Card(card_type=spcm.SPCM_TYPE_AO) as raw_card:
def rearrange_test(controller, num_segments,tuple_of_4,power_ramp_time,move_time,percentage_total_power_for_list,ramp_type):
    _1,_2,_3,_4 = tuple_of_4
    # raw_card = spcm.Card(card_type=spcm.SPCM_TYPE_AO)
    # raw_card.open()
    # controller = DDSRampController(raw_card)

    controller.run_the_procedure(1, num_segments, _1, _2, _3, _4, power_ramp_time, move_time, percentage_total_power_for_list, ramp_type)
    # input("Press Enter to Exit")
    # controller.run_the_procedure(1, num_segments, _1, _2, _3, _4, power_ramp_time,
    #                                 move_time, percentage_total_power_for_list, ramp_type)
    # input("Press Enter to Exit")
    # controller.run_the_procedure(2, num_segments, _1, _2, _3, _4, power_ramp_time,
    #                                 move_time, percentage_total_power_for_list, ramp_type)





    print(1)
    # input("Press Enter to Exit")
    # raw_card.close()