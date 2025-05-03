import numpy as np
import matplotlib.pyplot as plt


def Rearrangement_method__no_reservior_zyl_v2(target_array : np.array ,state_array : np.array):
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
    print(target_site_of_col_index_list)


    #获取某一非零列的所有原子行坐标
    for i in range(target_row_min,target_row_max + 1):
        if target_array[i,target_col_min] == 1:
            target_site_of_row_index_list.append(i)
    print(target_site_of_row_index_list)



    target_positions = [i for i, val in enumerate(target_array[:,target_col_min]) if val == 1]
    # 找出当前矩阵中原子的位置
    current_positions = [i for i, val in enumerate(state_array[:,target_col_min]) if val == 1]

    # 检查是否缺少足够的原子
    if len(target_positions) > len(current_positions):
        print('no enough atoms')  # 没有足够原子
        complete_moves = [[(0, 0, 0, 0)]]
    else:
        n = len(target_positions)
        m = len(current_positions)
        # 初始化最小步数为无穷大
        min_steps = float('inf')
        best_move_info = []
        from itertools import combinations
        # 生成所有可能的当前原子位置组合，长度为目标原子数量
        for comb in combinations(range(m), n):
            comb_positions = [current_positions[i] for i in comb]
            # 对当前组合的原子位置和目标位置排序
            comb_positions.sort()
            sorted_target = sorted(target_positions)
            move_info = []
            steps = 0
            valid = True
            # 标记已使用的原子位置
            used = [False] * m
            for j, start in enumerate(comb_positions):
                end = sorted_target[j]
                move = (start, end)
                # 检查移动是否交叉
                for k in range(m):
                    if not used[k] and k not in comb:
                        other_start = current_positions[k]
                        if (min(start, end) < other_start < max(start, end)):
                            valid = False
                            break
                if not valid:
                    break
                move_info.append(move)
                steps += abs(start - end)
                used[comb[j]] = True
            if valid and steps < min_steps:
                min_steps = steps
                best_move_info = move_info

        for i in range(len(best_move_info)):
            complete_moves_raw.append((best_move_info[i][0],target_col_min,best_move_info[i][1],target_col_min))
        complete_moves_no_pack = [tup for tup in complete_moves_raw if tup[0] != tup[2] or tup[1] != tup[3]]
        n_packed = 3
        for i in range(0, len(complete_moves_no_pack), n_packed):
            complete_moves.append(complete_moves_no_pack[i:i + n_packed])
    if complete_moves == []:
        complete_moves = [[(14,0,15,0)]]
    return complete_moves


def main(state_array:np.array):
    target_array = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
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
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                             [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]])
    complete_moves = Rearrangement_method__no_reservior_zyl_v2(target_array, state_array)
    print(complete_moves)
    return complete_moves




if __name__ == "__main__":
    state_array = np.array([
    [1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1],
    [0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0],
    [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1],
    [0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1],
    [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
])
    main(state_array)


