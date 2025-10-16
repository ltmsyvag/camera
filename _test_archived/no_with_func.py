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

    def ramp_slope_generate(self, num_segments, start_frequency_list, end_frequency_list, move_time, ramp_type):
        slopes = np.zeros((len(start_frequency_list), num_segments))
        x_axis_AOD_power_correction_coefficient_list = np.zeros((len(start_frequency_list), num_segments+1))
        x_axis_power_slopes = np.zeros((len(start_frequency_list), num_segments))
        t = np.linspace(0, 1, num_segments + 1, endpoint=True)
        for i in range(len(start_frequency_list)):
            parameters = {
                "startFreq_Hz": start_frequency_list[i],
                "endFreq_Hz": end_frequency_list[i],
                "time_s": move_time,
                "ramp_type": ramp_type
            }
            y = self.generate_function(t, parameters, num_segments)
            t_s = t * parameters["time_s"]
            sl_core = self.calculate_slope(t_s, y)
            slopes[i, :] = sl_core
            x_axis_AOD_fre_list = (y/10**6-101.4)/10.39
            x_axis_AOD_power_correction_coefficient = (0.8560/(0.0080*x_axis_AOD_fre_list**6-0.0028*x_axis_AOD_fre_list**5-0.0767*x_axis_AOD_fre_list**4+0.0200*x_axis_AOD_fre_list**3+0.1707*x_axis_AOD_fre_list**2-0.0466*x_axis_AOD_fre_list**1+0.7926))**1.1 #the power correction coefficient for the AOD on x-axis
            x_axis_AOD_power_correction_coefficient_list[i,:]=x_axis_AOD_power_correction_coefficient
            x_axis_power_sl = self.calculate_slope(t_s, x_axis_AOD_power_correction_coefficient)
            x_axis_power_slopes[i, :] = x_axis_power_sl
        self.slopes = slopes
        self.x_axis_power_slopes = x_axis_power_slopes
        self.x_axis_AOD_power_correction_coefficient_list = x_axis_AOD_power_correction_coefficient_list
        

    def execute_ramp(self, num_segments, single_frequency ,start_frequency_list, end_frequency_list, power_ramp_time ,move_time, percentage_total_power_for_list):
        number_of_frequencies = len(start_frequency_list)
        random_phase_list = [random.randint(0,360)for i in range(number_of_frequencies)] #generate the random phase list for different dds core
        period_s = move_time/num_segments
        power_ramp_period_s = power_ramp_time
        self.dds.freq_ramp_stepsize(4096)  #important note: don't set this in dds_config, otherwise the frequency slope will be so faster than expected
        self.dds.amp_ramp_stepsize(4096)
        self.dds.trg_timer(1e-6)
        self.dds.write_to_card()
        # self.dds.exec_now()
        # for i in range(number_of_frequencies):
        #     self.dds[i].amp(0) #start power ramp
        # self.dds.exec_at_trg()
        # self.dds.write_to_card()



        """step 1 generate waveform data and ramp the power"""
        for i in range(number_of_frequencies):
            self.dds[i].amplitude_slope(self.x_axis_AOD_power_correction_coefficient_list[i,0]*percentage_total_power_for_list/5/power_ramp_period_s) #start power ramp, note the power is corrected by the AOD power correction coefficient
            self.dds[i].freq(start_frequency_list[i])
            self.dds[i].phase(random_phase_list[i])
        self.dds[20].amp(0.4)
        self.dds[20].freq(single_frequency)
        self.dds.trg_timer(power_ramp_period_s)
        self.dds.exec_at_trg()
        self.dds.write_to_card()
        #stop power ramp
        for i in range(number_of_frequencies):
            self.dds[i].amplitude_slope(0)
            self.dds[i].amp(self.x_axis_AOD_power_correction_coefficient_list[i,0]*percentage_total_power_for_list/5)
        self.dds.trg_timer(10e-6) #wait for 100us to stablize the aod tweezer
        self.dds.exec_at_trg()
        self.dds.write_to_card()

        """step 2 start frequency ramp"""
        self.dds.trg_timer(period_s)
        for j in range(num_segments):
            for i in range(number_of_frequencies):
                self.dds[i].frequency_slope(self.slopes[i][j]) # Hz/s
                self.dds[i].amp(self.x_axis_AOD_power_correction_coefficient_list[i][j+1]*percentage_total_power_for_list/5)  # V/s
            self.dds.exec_at_trg()

        """step 3 stop frequency ramp"""
        for i in range(number_of_frequencies):
            self.dds[i].frequency_slope(0)
            #self.dds[i].amplitude_slope(0)  # stop frequency ramp
            self.dds[i].freq(end_frequency_list[i])
            self.dds[i].amp(self.x_axis_AOD_power_correction_coefficient_list[i,num_segments]*percentage_total_power_for_list/5)
        self.dds.trg_timer(1e-6)
        self.dds.exec_at_trg()
        self.dds.write_to_card()

        """step 4 stop output"""
        for i in range(number_of_frequencies):
            self.dds[i].amplitude_slope(self.x_axis_AOD_power_correction_coefficient_list[i,num_segments]*(-percentage_total_power_for_list) / 5 / power_ramp_period_s)  # start power ramp down
        self.dds.trg_timer(power_ramp_period_s)
        self.dds.exec_at_trg()
        for i in range(number_of_frequencies):
            self.dds[i].amplitude_slope(0)  # stop power ramp down
            self.dds[i].amp(0)
        self.dds.trg_timer(1e-6)
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
            self.ramp_slope_generate(num_segments = num_segments, start_frequency_list = start_frequency_table[i], end_frequency_list = end_frequency_table[i], move_time = move_time, ramp_type = ramp_type)
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
def rearrange(controller, num_segments,tuple_of_4,power_ramp_time,move_time,percentage_total_power_for_list,ramp_type):
    _1,_2,_3,_4 = tuple_of_4
    # raw_card = spcm.Card(card_type=spcm.SPCM_TYPE_AO)
    # raw_card.open()
    # controller = DDSRampController(raw_card)

    controller.run_the_procedure(0, num_segments, _1, _2, _3, _4, power_ramp_time, move_time, percentage_total_power_for_list, ramp_type)
    # input("Press Enter to Exit")
    # controller.run_the_procedure(1, num_segments, _1, _2, _3, _4, power_ramp_time,
    #                                 move_time, percentage_total_power_for_list, ramp_type)
    # input("Press Enter to Exit")
    # controller.run_the_procedure(2, num_segments, _1, _2, _3, _4, power_ramp_time,
    #                                 move_time, percentage_total_power_for_list, ramp_type)





    print(1)
    # input("Press Enter to Exit")
    # raw_card.close()