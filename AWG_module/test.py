import torch
import time as tt
class YourClass:
    def s_curve(self, t):
        """S形曲线函数: 6t⁵ - 15t⁴ + 10t³"""
        return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3

    def s_curve_integral(self, t):
        """S形曲线函数的积分: t⁶ - 3t⁵ + 2.5t⁴"""
        return t ** 6 - 3 * t ** 5 + 2.5 * t ** 4

    def generate_fm_waveform(self,
            move_time=1e-3,        # 总持续时间(秒)
            rise_time=1e-3,        # 幅度上升时间(秒)
            fall_time=1e-3,        # 幅度下降时间(秒)
            sampling_rate=1e6,    # 采样率(Hz)
            base_freq=89e6,       # 起始频率(Hz)
            max_freq=95e6,        # 最大频率(Hz)
            max_amplitude=1,      # 最大幅度
            device='cuda'         # 'cuda' 或 'cpu'
    ):
        """
        生成带S形幅度变化的S形扫频波形（GPU加速）
        返回值：t, waveform, freq_profile, amplitude_profile（全部是 numpy）
        """
        device = torch.device(device)

        duration = move_time + rise_time + fall_time
        total_samples = int(round(sampling_rate * duration))
        rise_samples = int(sampling_rate * rise_time)
        fall_samples = int(sampling_rate * fall_time)
        steady_samples = int(sampling_rate * move_time)

        if steady_samples < 0:
            raise ValueError("上升时间+下降时间不能超过总持续时间")

        sweep_start = rise_samples
        sweep_end = sweep_start + steady_samples

        # 时间轴
        t = torch.linspace(0, duration, total_samples, device=device)

        # 频率轮廓
        freq_profile = torch.ones(total_samples, device=device) * base_freq
        if steady_samples > 0:
            sweep_t = torch.linspace(0, 1, steady_samples, device=device)
            freq_profile[sweep_start:sweep_end] = base_freq + (max_freq - base_freq) * self.s_curve(sweep_t)
        freq_profile[sweep_end:] = max_freq

        # 幅度轮廓
        amplitude_profile = torch.ones(total_samples, device=device) * max_amplitude
        if rise_samples > 0:
            rise_t = torch.linspace(0, 1, rise_samples, device=device)
            amplitude_profile[:rise_samples] = max_amplitude * self.s_curve(rise_t)
        if fall_samples > 0:
            fall_start = total_samples - fall_samples
            fall_t = torch.linspace(0, 1, fall_samples, device=device)
            amplitude_profile[fall_start:] = max_amplitude * (1 - self.s_curve(fall_t))

        # 实际波形可以忽略
        waveform = torch.zeros_like(t, device=device)

        # 返回 numpy（方便后续）
        return (t.cpu().numpy(),
                waveform.cpu().numpy(),
                freq_profile.cpu().numpy(),
                amplitude_profile.cpu().numpy())
if __name__ == "__main__":
    obj = YourClass()
    t, waveform, freq, amp = obj.generate_fm_waveform(device='cpu')  # GPU
    t1 = tt.time()
    for i in range():
        # 生成波形
        # 你可以选择使用 GPU 或 CPU
        # 如：
        t, waveform, freq, amp = obj.generate_fm_waveform(device='cpu')  # GPU
    # 或：t, waveform, freq, amp = obj.generate_fm_waveform(device='cpu')  # CPU
    t2 = tt.time()
    print(t2-t1)