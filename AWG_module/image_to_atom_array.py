import numpy as np


def image_process(image, nx, ny, x0, y0, x1, y1, x2, y2, x3, y3, rec_x, rec_y, count_threshold):
    """
    改进版光镊掩模生成与原子判断

    参数说明：
    rec_x, rec_y -> MATLAB中dx_rec/dy_rec参数，固定为3（生成3×3区域）
    实际掩模尺寸：(rec_x+1) x (rec_y+1) = 3x3
    """
    image = image.astype(float)

    mask = np.zeros_like(image, dtype=np.uint8)
    atom_array = np.zeros((ny, nx), dtype=np.uint8)

    # 基矢增量计算
    dx_xi = (x2 - x1) / (nx - 1)  # X基矢的x增量
    dy_xi = (y2 - y1) / (nx - 1)  # X基矢的y增量
    dx_yi = (x3 - x1) / (ny - 1)  # Y基矢的x增量
    dy_yi = (y3 - y1) / (ny - 1)  # Y基矢的y增量

    for i in range(nx):  # MATLAB索引风格（从1开始模拟）
        for j in range(ny):
            # 排除中心区域（MATLAB原逻辑）
            # if (i + 1 == 10 or i + 1 == 11) and (j + 1 == 10 or j + 1 == 11):
            #     continue

            # 计算左上角坐标（对应MATLAB的x0+round(...)）
            x = x0 + round((j) * (dx_yi) + (i) * (dx_xi))  # MATLAB索引从1开始，故用j=0对应原j=1
            y = y0 + round((j) * (dy_yi) + (i) * (dy_xi))

            # 生成3×3掩模（MATLAB的x:x+2语法）
            x_end = x + rec_x + 1  # rec_x=2时，x+3实现x:x+2
            y_end = y + rec_y + 1

            # 边界保护
            if x_end > image.shape[1] or y_end > image.shape[0]:
                continue

            # 设置掩模区域
            mask[y-1:y_end-1, x-1:x_end-1] = 1

            # 原子存在判断
            cell = (image[y:y_end, x:x_end] - 800)/0.9*0.1# 220为背景噪声,光子数转换效率是/0.9*0.1
            if np.sum(cell) > count_threshold: #
                
                atom_array[j, i] = 1  # 注意坐标对应关系           
            else:
                atom_array[j, i] = 0
    print(atom_array)
    return mask, atom_array


# 验证测试
def test_corrected():
    # 创建带有特征点的测试图像
    test_img = np.zeros((256, 256), dtype=np.uint16)

    # 在已知坐标设置高信号（对应掩模位置）
    test_img[9:12, 99:102] = 1000  # (y,x) = (50,60)
    test_img[99:102, 9:12] = 1500  # (y,x) = (103,55)

    # 调用函数（参数对应MATLAB示例）
    mask, atoms = image_process(
        image=test_img,
        nx=10, ny=10,
        x0=9, y0=9,  # MATLAB中的x0 = x1-1 =53-1
        x1=10, y1=10,  # 基准点1
        x2=100, y2=10,  # X基矢终点
        x3=10, y3=100,  # Y基矢终点
        rec_x=2, rec_y=2,  # 保持与MATLAB相同参数
        count_threshold=50
    )

    # 结果验证
    print("原子阵列检测结果：\n", atoms)

    # 可视化
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    ax[0].imshow(test_img, cmap='gray')
    ax[0].set_title('input')

    ax[1].imshow(mask, cmap='gray')
    ax[1].set_title('3x3mask')

    ax[2].imshow(atoms, cmap='viridis')
    ax[2].set_title('atom')
    plt.show()
    print(atoms)

if __name__ == "__main__":
    test_corrected()
