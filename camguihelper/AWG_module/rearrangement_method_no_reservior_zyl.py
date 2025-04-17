import numpy as np
import matplotlib.pyplot as plt


def Rearrangement_method__no_reservior_zyl(target_array : np.array ,state_array : np.array):
    target_site_of_col_index_list = []
    target_site_of_row_index_list = []
    atom_possible_group_row_index_list = []
    complete_moves_raw = []
    complete_moves_no_pack = []
    complete_moves = []
    nrows = 16
    ncols = 16
    target_col_min = 0  # 0 indexed
    target_row_min = 0
    for i in range(ncols):
        if np.sum(target_array[:, i]) == 0:
            target_col_min += 1
        else:
            break
    for i in range(nrows):
        if np.sum(target_array[i]) == 0:
            target_row_min += 1
        else:
            break
    target_row_max = nrows - 1  # 0 indexed, inclusive
    target_col_max = ncols - 1  # 0 indexed, inclusive
    for i in range(ncols):
        if np.sum(target_array[:, ncols - 1 - i]) == 0:
            target_col_max -= 1
        else:
            break
    for i in range(nrows):
        if np.sum(target_array[nrows - 1 - i]) == 0:
            target_row_max -= 1
        else:
            break


    #获取所有存在原子分布的列对应坐标
    for i in range(target_col_min,target_col_max + 1):
        if np.sum(target_array[:, i]) > 0:
            target_site_of_col_index_list.append(i)



    #获取某一非零列的所有原子行坐标
    for i in range(target_row_min,target_row_max + 1):
        if target_array[i,target_col_min] == 1:
            target_site_of_row_index_list.append(i)


    # 获取实际阵列对应列的原子坐标
    state_array_nozero_col = state_array[:,target_col_min]
    atom_non_zero_indices = np.nonzero(state_array_nozero_col)[0]
    # 获取非零元素的个数
    atom_count = len(atom_non_zero_indices)
    # 构建完整的坐标（行索引和列索引）
    full_coordinates = [int(row_index) for row_index in atom_non_zero_indices]


    # 贪心算法获取所有可能的原子组合，最后选取与目标点位距离最小的组合作为重排的选择
    if len(target_site_of_row_index_list) > atom_count:
        print('no enough atoms') #没有足够原子
        complete_moves = [[(14,0,15,0)]]
    else:
        for i in range(0,atom_count - len(target_site_of_row_index_list) + 1):
            atom_possible_group_row_index_list.append(full_coordinates[i:i + len(target_site_of_row_index_list)])

        # 计算第一个子列表与目标列表对应元素差值的绝对值之和
        min_diff = sum(abs(a - b) for a, b in zip(atom_possible_group_row_index_list[0], target_site_of_row_index_list))
        min_index = 0
        # 从第二个子列表开始遍历
        for i in range(1, len(atom_possible_group_row_index_list)):
            sub_list = atom_possible_group_row_index_list[i]
            # 计算当前子列表与目标列表对应元素差值的绝对值之和
            diff = sum(abs(a - b) for a, b in zip(sub_list, target_site_of_row_index_list))
            # 如果当前差值小于最小差值，则更新最小差值和对应的子列表索引
            if diff < min_diff:
                min_diff = diff
                min_index = i
        atom_group_row_index_list = atom_possible_group_row_index_list[min_index]
        for i in range(len(atom_group_row_index_list)):
            complete_moves_raw.append((atom_group_row_index_list[i],target_col_min,target_site_of_row_index_list[i], target_col_min))
        complete_moves_no_pack = [tup for tup in complete_moves_raw if tup[0] != tup[2] or tup[1] != tup[3]]
        n_packed = 2
        for i in range(0, len(complete_moves_no_pack), n_packed):
            complete_moves.append(complete_moves_no_pack[i:i + n_packed])
    if complete_moves == []:
        complete_moves = [[(14,0,15,0)]]
    return complete_moves


def main(state_array:np.array):
    target_array = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
    complete_moves = Rearrangement_method__no_reservior_zyl(target_array, state_array)
    print(complete_moves)
    return complete_moves



if __name__ == "__main__":
    state_array = np.array([[0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
    main(state_array)


