import numpy as np
import matplotlib.pyplot as plt


class ArbitraryMultipleTweezersMoveCalc():
    def __init__(self, nrows, ncols, reservoir_lower_num, reservoir_upper_num, target_array, capture_time, move_time,
                 reconfig_num=1):
        self.nrows = nrows
        self.ncols = ncols
        # here we only specify the num of reservoir instead of the rows, so we don't
        # restrict ourselves to always having to fill up certain rows for the reservoir
        # which requires more tweezers turned on. Instead, as long as enough atoms are
        # kept somewhere in the reservoir, that is fine.
        self.reservoir_size = reservoir_lower_num + reservoir_upper_num
        self.reservoir_lower_num = reservoir_lower_num
        self.reservoir_upper_num = reservoir_upper_num
        self.target_array = target_array
        self.reconfig_num = reconfig_num
        self.target_col_min = 0  # 0 indexed
        self.target_row_min = 0
        for i in range(self.ncols):
            if np.sum(self.target_array[:, i]) == 0:
                self.target_col_min += 1
            else:
                break
        for i in range(self.nrows):
            if np.sum(self.target_array[i]) == 0:
                self.target_row_min += 1
            else:
                break
        self.target_row_max = self.nrows - 1  # 0 indexed, inclusive
        self.target_col_max = self.ncols - 1  # 0 indexed, inclusive
        for i in range(self.ncols):
            if np.sum(self.target_array[:, self.ncols - 1 - i]) == 0:
                self.target_col_max -= 1
            else:
                break
        for i in range(self.nrows):
            if np.sum(self.target_array[self.nrows - 1 - i]) == 0:
                self.target_row_max -= 1
            else:
                break
        self.reservoir_rows_lower = list(range(self.target_row_min))  # defined as lower indices
        self.reservoir_rows_upper = list(range(self.target_row_max + 1, self.nrows))
        if len(self.reservoir_rows_upper) < self.reservoir_upper_num:
            raise Exception('Reservoir Error')
        if len(self.reservoir_rows_lower) < self.reservoir_lower_num:
            raise Exception('Reservoir Error')
        self.reservoir_rows = self.reservoir_rows_lower + self.reservoir_rows_upper
        if len(self.reservoir_rows_lower) <= len(self.reservoir_rows_upper):
            self.lower = True  # this bool determines if lower is smaller or not in reservoir size
        else:
            self.lower = False
        self.target_n_cols = self.target_col_max - self.target_col_min + 1
        self.center_col = (self.target_col_min + self.target_col_max) * 0.5
        self.center_row = (self.target_row_min + self.target_row_max) * 0.5
        self.capture_time = capture_time
        self.move_time = move_time
        self.loading_prob = 0.55
        self.loss_prob = 0.06
        self.generate_helper_table()

    def generate_helper_table(self):
        """
        Generates the 2D array of value = (row,col)
        """
        self.helper_table = np.zeros((self.nrows, self.ncols), dtype=object)
        for i in range(self.nrows):
            for j in range(self.ncols):
                self.helper_table[i, j] = (i, j)

    def get_new_starting_state(self):
        valid_start_state = False
        while not valid_start_state:
            state = np.where(np.random.uniform(0, 1, (self.nrows, self.ncols)) <= self.loading_prob, 1, 0).astype(
                np.int32)
            # Training assumes we have a valid starting state i.e. number of loaded atoms >= n^2.
            if np.count_nonzero(state == 1) >= np.count_nonzero(self.target_array):
                valid_start_state = True
        self.state = state
        return state

    def set_state(self, state):
        self.state = state

    def update_state(self, moveset):
        for row in moveset:
            for move in row:
                self.state[move[0], move[1]] = 0
            for move in row:
                if move[2] != self.nrows and move[2] != -1 and move[3] != self.ncols and move[3] != -1:
                    self.state[move[2], move[3]] = 1

    def introduce_defects(self):
        mask = np.where(np.random.uniform(0, 1, (self.nrows, self.ncols)) >= self.loss_prob, 1, 0).astype(np.int32)
        self.set_state(mask * self.state)
        self.state[5, 17] = 1

    def get_minimal_moves(self, before_indices, after_indices, min_index, max_index):
        # Returns the moves using minimal tweezers when len(before_indices)>len
        before_indices_combi = []
        before_indices_complement_left = []
        before_indices_complement_right = []
        best_combi = None
        best_combi_complement_left = None
        best_combi_complement_right = None
        best_score = -999
        if before_indices[0][0] == before_indices[1][0]:
            row = True
        else:
            row = False
        for i in range(len(before_indices) - len(after_indices) + 1):
            combi = before_indices[i:i + len(after_indices)]
            complement_left = before_indices[:i]
            complement_right = before_indices[i + len(after_indices):]
            if row:
                if combi[-1][1] >= max_index[1] and combi[0][1] <= min_index[1]:
                    before_indices_combi.append(combi)
                    before_indices_complement_left.append(complement_left)
                    before_indices_complement_right.append(complement_right)
            else:
                if combi[-1][0] >= max_index[0] and combi[0][0] <= min_index[0]:
                    before_indices_combi.append(combi)
                    before_indices_complement_left.append(complement_left)
                    before_indices_complement_right.append(complement_right)
        # print(before_indices_combi)
        for k in range(len(before_indices_combi)):
            # calc similarity between combi and after_indices
            score = np.count_nonzero(combi == after_indices)
            if score > best_score:
                best_score = score
                best_combi = before_indices_combi[k]
                best_combi_complement_left = before_indices_complement_left[k]
                best_combi_complement_right = before_indices_complement_right[k]
        if row:
            moves = [best_combi_complement_left[i] + (before_indices[0][0], -1) for i in
                     range(len(best_combi_complement_left))] + [best_combi[i] + after_indices[i] for i in
                                                                range(len(after_indices))] + [
                        best_combi_complement_right[i] + (before_indices[0][0], self.ncols) for i in
                        range(len(best_combi_complement_right))]
        else:
            moves = [best_combi_complement_left[i] + (-1, before_indices[0][1]) for i in
                     range(len(best_combi_complement_left))] + [best_combi[i] + after_indices[i] for i in
                                                                range(len(after_indices))] + [
                        best_combi_complement_right[i] + (self.nrows, before_indices[0][1]) for i in
                        range(len(best_combi_complement_right))]
        filtered_moves = list(filter(lambda x: x[0] != x[2] or x[1] != x[3], moves))
        return filtered_moves

    def row_sorting(self, atom_array, array_indices, excess=None):
        atom_loc_in_array = np.nonzero(atom_array == 1)[0]
        initial_indices = array_indices[atom_loc_in_array]
        no_atoms = len(initial_indices)
        if no_atoms == self.target_n_cols:  # just nice, we have enough atoms to help the target cols
            final_indices = array_indices[self.target_col_min:self.target_col_max + 1]
            moves = [initial_indices[i] + final_indices[i] for i in range(len(initial_indices))]
            filtered_moves = list(filter(lambda x: x[0] != x[2] or x[1] != x[3], moves))
        elif no_atoms > self.target_n_cols:  # more than enough atoms
            final_indices = array_indices[self.target_col_min:self.target_col_max + 1]
            distance_to_center = abs(atom_loc_in_array - self.center_col)
            initial_indices_sorted = [x for _, x in sorted(zip(distance_to_center, initial_indices))]
            initial_indices_mid = initial_indices_sorted[:self.target_n_cols]
            initial_indices_mid.sort(key=lambda x: x[1])
            moves = [initial_indices_mid[i] + final_indices[i] for i in range(len(initial_indices_mid))]
            filtered_moves = list(filter(lambda x: x[0] != x[2] or x[1] != x[3], moves))
        else:
            # Calc excess only for the relevant cols inside the target
            if not type(excess) == np.ndarray:
                net_atom_counts_col = np.sum(self.state - self.target_array, axis=0) - atom_array
                net_atom_counts_col = net_atom_counts_col[self.target_col_min:self.target_col_max + 1]
            else:
                net_atom_counts_col = excess - atom_array[self.target_col_min:self.target_col_max + 1]
            # Obtain the rank of cols based on the fewest excess atoms
            cols_rank_indices = array_indices[[x for _, x in sorted(
                zip(net_atom_counts_col, list(range(self.target_col_min, self.target_col_max + 1))), reverse=False)]]
            final_indices = cols_rank_indices[:len(initial_indices)]
            final_indices.sort()
            moves = [initial_indices[i] + final_indices[i] for i in range(len(initial_indices))]
            filtered_moves = list(filter(lambda x: x[0] != x[2] or x[1] != x[3], moves))

        return filtered_moves

    def eject_col(self, atom_array, array_indices):
        """
        Send all down V+
        maybe next time do left and right separately
        """
        atom_loc_in_array = np.nonzero(atom_array == 1)[0]
        initial_indices = array_indices[atom_loc_in_array]
        moves = [initial_indices[i] + (self.nrows, initial_indices[0][1]) for i in range(len(initial_indices))]
        filtered_moves = list(filter(lambda x: x[0] != x[2] or x[1] != x[3], moves))
        return filtered_moves

    def compress_col(self, atom_array, target_array, array_indices):
        """
        compress towards V-, target_array = actual_target + reservoir_sites
        if num_atoms < actual_target, fill towards center
        elif num_atoms == actual_target, fill everything
        else
        """
        atom_loc_in_array = np.nonzero(atom_array == 1)[0]
        initial_indices = array_indices[atom_loc_in_array]
        final_indices = list(array_indices[np.nonzero(target_array == 1)[0]])
        num_atoms = len(initial_indices)
        num_target = len(final_indices)
        if num_atoms <= num_target:
            # just fill into center of target array
            s = (num_target - num_atoms + 1) // 2
            final_indices = final_indices[s:s + num_atoms]
        else:
            # num_atoms > num_target.
            if num_atoms >= num_target + self.reservoir_size:
                # more than enough atoms to fill up the reservoir too
                if self.reservoir_lower_num == 0 and self.reservoir_upper_num == 0:
                    final_indices = final_indices
                elif self.reservoir_lower_num == 0:
                    final_indices = final_indices + [(x, initial_indices[0][1]) for x in
                                                     self.reservoir_rows_upper[-self.reservoir_upper_num:]]
                elif self.reservoir_upper_num == 0:
                    final_indices = [(x, initial_indices[0][1]) for x in
                                     self.reservoir_rows_lower[:self.reservoir_lower_num]] + final_indices
                else:
                    final_indices = [(x, initial_indices[0][1]) for x in
                                     self.reservoir_rows_lower[:self.reservoir_lower_num]] + final_indices + [
                                        (x, initial_indices[0][1]) for x in
                                        self.reservoir_rows_upper[-self.reservoir_upper_num:]]
                if num_atoms != len(final_indices):
                    # too many atoms, eject the rest
                    excess_atoms = num_atoms - len(final_indices)
                    final_indices = final_indices + [(self.nrows, initial_indices[0][1])] * excess_atoms
            else:
                if np.sum(atom_array[self.target_row_min:self.target_row_max + 1]) <= num_target:
                    # if target array is lacking atoms, then bring in just enough from reservoir, leaving the other
                    # reservoir atoms that were unused untouched.
                    distance_to_center = abs(atom_loc_in_array - self.center_row)
                    initial_indices_sorted = [x for _, x in sorted(zip(distance_to_center, initial_indices))]
                    initial_indices = initial_indices_sorted[:num_target]
                    initial_indices.sort(key=lambda x: x[0])
                else:
                    # we need to bring some atoms out to the reservoir, no ejection though
                    excess_atoms = num_atoms - num_target  # no. of atoms in excess compared to target
                    if self.lower:
                        lower_reservoir_atoms_to_fill = min(self.reservoir_lower_num, excess_atoms // 2)
                        upper_reservoir_atoms_to_fill = excess_atoms - lower_reservoir_atoms_to_fill
                    else:
                        upper_reservoir_atoms_to_fill = min(self.reservoir_upper_num, excess_atoms // 2)
                        lower_reservoir_atoms_to_fill = excess_atoms - upper_reservoir_atoms_to_fill
                    if lower_reservoir_atoms_to_fill == 0:
                        final_indices = final_indices + [(x, initial_indices[0][1]) for x in
                                                         self.reservoir_rows_upper[-upper_reservoir_atoms_to_fill:]]
                    elif upper_reservoir_atoms_to_fill == 0:
                        final_indices = [(x, initial_indices[0][1]) for x in
                                         self.reservoir_rows_lower[:lower_reservoir_atoms_to_fill]] + final_indices
                    else:
                        final_indices = [(x, initial_indices[0][1]) for x in
                                         self.reservoir_rows_lower[:lower_reservoir_atoms_to_fill]] + final_indices + [
                                            (x, initial_indices[0][1]) for x in
                                            self.reservoir_rows_upper[-upper_reservoir_atoms_to_fill:]]

        moves = [initial_indices[i] + final_indices[i] for i in range(len(initial_indices))]
        filtered_moves = list(filter(lambda x: x[0] != x[2] or x[1] != x[3], moves))
        return filtered_moves

    def generate_moves(self, reconfig_round=1, threshold=1):
        self.complete_move_set = []
        counter = None
        if reconfig_round == 1:
            # Do Round 1 of reconfiguration here
            # Do row sorting for all rows (order doesn't matter)
            # for the first reconfig's row sorting, we do all rows to equalise the vacancies
            atom_counts_row = np.sum(self.state, axis=1)
            row_sorting_order = [x for _, x in sorted(zip(atom_counts_row, list(range(0, self.nrows))), reverse=True)]
            for row_index in row_sorting_order:
                moves = self.row_sorting(self.state[row_index], self.helper_table[row_index])
                # print('row',row_index,filtered_moves)
                if len(moves) > 0:
                    while len(moves) > threshold:
                        # divide
                        z = 0
                        # print(moves)
                        while z != len(moves) and moves[z][3] - moves[z][1] > 0:
                            z += 1
                        # z is the first index where moving changes direction
                        if z >= threshold:
                            moves1 = moves[z - threshold:z]
                            moves = moves[:z - threshold] + moves[z:]
                        else:
                            moves1 = moves[z:z + threshold]
                            moves = moves[:z] + moves[z + threshold:]

                        # self.complete_move_set.append(moves)
                        self.complete_move_set.append(moves1)
                        self.update_state([moves1])
                    # else:
                    self.complete_move_set.append(moves)
                    self.update_state([moves])
                # net_atom_counts_col = np.sum(self.state,axis=0) - np.sum(self.target_array,axis=0)
                # net_atom_counts_col = net_atom_counts_col[self.target_col_min:self.target_col_max+1]
                # print(net_atom_counts_col)
            solved = False
            excess = np.sum(self.state - self.target_array, axis=0)
            excess = excess[self.target_col_min:self.target_col_max + 1]
            if (excess >= 0).all():
                # solved
                solved = True
                # print('no change')
            if not solved:
                reservoir = self.state[self.reservoir_rows]
                criteria = np.abs(np.sum(reservoir, axis=1) - self.target_n_cols // 2)
                row_sorting_order = [x for _, x in sorted(zip(criteria, self.reservoir_rows), reverse=False)]
                for row_index in row_sorting_order:
                    moves = self.row_sorting(self.state[row_index], self.helper_table[row_index], excess)
                    # print(filtered_moves)
                    if len(moves) > 0:
                        while len(moves) > threshold:
                            # divide
                            z = 0
                            # print(moves)
                            while z != len(moves) and moves[z][3] - moves[z][1] > 0:
                                z += 1
                            # z is the first index where moving changes direction
                            if z >= threshold:
                                moves1 = moves[z - threshold:z]
                                moves = moves[:z - threshold] + moves[z:]
                            else:
                                moves1 = moves[z:z + threshold]
                                moves = moves[:z] + moves[z + threshold:]

                            # self.complete_move_set.append(moves)
                            self.complete_move_set.append(moves1)
                            self.update_state([moves1])
                        # else:
                        self.complete_move_set.append(moves)
                        self.update_state([moves])

                    excess = np.sum(self.state - self.target_array, axis=0)
                    excess = excess[self.target_col_min:self.target_col_max + 1]
                    if (excess >= 0).all():
                        # solved
                        solved = True
                        break
            if not solved:
                non_reservoir_indices = list(range(self.target_row_min - 1, self.target_row_max))
                non_reservoir = self.state[non_reservoir_indices]
                criteria = np.sum(non_reservoir, axis=1)
                row_sorting_order = [x for _, x in sorted(zip(criteria, non_reservoir_indices), reverse=False)]
                for row_index in row_sorting_order:
                    moves = self.row_sorting(self.state[row_index], self.helper_table[row_index], excess)
                    # print(filtered_moves)
                    if len(moves) > 0:
                        while len(moves) > threshold:
                            # divide
                            z = 0
                            # print(moves)
                            while z != len(moves) and moves[z][3] - moves[z][1] > 0:
                                z += 1
                            # z is the first index where moving changes direction
                            if z >= threshold:
                                moves1 = moves[z - threshold:z]
                                moves = moves[:z - threshold] + moves[z:]
                            else:
                                moves1 = moves[z:z + threshold]
                                moves = moves[:z] + moves[z + threshold:]

                            # self.complete_move_set.append(moves)
                            self.complete_move_set.append(moves1)
                            self.update_state([moves1])
                        # else:
                        self.complete_move_set.append(moves)
                        self.update_state([moves])
                    excess = np.sum(self.state - self.target_array, axis=0)
                    excess = excess[self.target_col_min:self.target_col_max + 1]
                    if (excess >= 0).all():
                        # solved
                        solved = True
                        break
            # Now do column compression
            # print(self.state)
            # net_atom_counts_col = np.sum(self.state,axis=0) - np.sum(self.target_array,axis=0)
            # net_atom_counts_col = net_atom_counts_col[self.target_col_min:self.target_col_max+1]
            # print(net_atom_counts_col)

            # First we eject the cols outside target cols
            for col_index in list(range(self.target_col_min)) + list(range(self.target_col_max + 1, self.ncols)):
                filtered_moves = self.eject_col(self.state[:, col_index], self.helper_table[:, col_index])
                # print('eject',col_index,filtered_moves)
                if len(filtered_moves) > 0:
                    while len(filtered_moves) > threshold:
                        moves1 = filtered_moves[-threshold:]
                        filtered_moves = filtered_moves[:len(filtered_moves) - threshold]
                        self.complete_move_set.append(moves1)
                        self.update_state([moves1])
                    self.complete_move_set.append(filtered_moves)
                    self.update_state([filtered_moves])
            # Next we compress the target cols
            for col_index in range(self.target_col_min, self.target_col_max + 1):
                moves = self.compress_col(self.state[:, col_index], self.target_array[:, col_index],
                                          self.helper_table[:, col_index])
                # print('compress',col_index,filtered_moves)
                if len(moves) > 0:
                    while len(moves) > threshold:
                        # divide
                        z = 0
                        # print(moves)
                        while z != len(moves) and moves[z][2] - moves[z][0] > 0:
                            z += 1
                        # z is the first index where moving changes direction
                        if z >= threshold:
                            moves1 = moves[z - threshold:z]
                            moves = moves[:z - threshold] + moves[z:]
                        else:
                            moves1 = moves[z:z + threshold]
                            moves = moves[:z] + moves[z + threshold:]

                        # self.complete_move_set.append(moves)
                        self.complete_move_set.append(moves1)
                        self.update_state([moves1])
                    # else:
                    self.complete_move_set.append(moves)
                    self.update_state([moves])
        else:
            # sometimes the first round may not have gotten rid of the cols outside target, so try again
            for col_index in list(range(self.target_col_min)) + list(range(self.target_col_max + 1, self.ncols)):
                filtered_moves = self.eject_col(self.state[:, col_index], self.helper_table[:, col_index])
                if len(filtered_moves) > 0:
                    while len(filtered_moves) > threshold:
                        moves1 = filtered_moves[-threshold:]
                        filtered_moves = filtered_moves[:len(filtered_moves) - threshold]
                        self.complete_move_set.append(moves1)
                        self.update_state([moves1])
                    self.complete_move_set.append(filtered_moves)
                    self.update_state([filtered_moves])
            # do row sorting for the reservoir rows only
            solved = False
            counter = 0
            excess = np.sum(self.state - self.target_array, axis=0)
            excess = excess[self.target_col_min:self.target_col_max + 1]
            if (excess >= 0).all():
                # solved
                solved = True
                # print('no change')
            if not solved:
                reservoir = self.state[self.reservoir_rows]
                criteria = np.abs(np.sum(reservoir, axis=1) - self.target_n_cols // 2)
                row_sorting_order = [x for _, x in sorted(zip(criteria, self.reservoir_rows), reverse=False)]
                for row_index in row_sorting_order:
                    counter += 1
                    moves = self.row_sorting(self.state[row_index], self.helper_table[row_index], excess)
                    # print(filtered_moves)
                    if len(moves) > 0:
                        while len(moves) > threshold:
                            # divide
                            z = 0
                            # print(moves)
                            while z != len(moves) and moves[z][3] - moves[z][1] > 0:
                                z += 1
                            # z is the first index where moving changes direction
                            if z >= threshold:
                                moves1 = moves[z - threshold:z]
                                moves = moves[:z - threshold] + moves[z:]
                            else:
                                moves1 = moves[z:z + threshold]
                                moves = moves[:z] + moves[z + threshold:]

                            # self.complete_move_set.append(moves)
                            self.complete_move_set.append(moves1)
                            self.update_state([moves1])
                        # else:
                        self.complete_move_set.append(moves)
                        self.update_state([moves])

                    excess = np.sum(self.state - self.target_array, axis=0)
                    excess = excess[self.target_col_min:self.target_col_max + 1]
                    if (excess >= 0).all():
                        # solved
                        solved = True
                        break
            if not solved:
                non_reservoir_indices = list(range(self.target_row_min - 1, self.target_row_max))
                non_reservoir = self.state[non_reservoir_indices]
                criteria = np.sum(non_reservoir, axis=1)
                row_sorting_order = [x for _, x in sorted(zip(criteria, non_reservoir_indices), reverse=False)]
                for row_index in row_sorting_order:
                    counter += 1
                    moves = self.row_sorting(self.state[row_index], self.helper_table[row_index], excess)
                    # print(filtered_moves)
                    if len(moves) > 0:
                        while len(moves) > threshold:
                            # divide
                            z = 0
                            # print(moves)
                            while z != len(moves) and moves[z][3] - moves[z][1] > 0:
                                z += 1
                            # z is the first index where moving changes direction
                            if z >= threshold:
                                moves1 = moves[z - threshold:z]
                                moves = moves[:z - threshold] + moves[z:]
                            else:
                                moves1 = moves[z:z + threshold]
                                moves = moves[:z] + moves[z + threshold:]

                            # self.complete_move_set.append(moves)
                            self.complete_move_set.append(moves1)
                            self.update_state([moves1])
                        # else:
                        self.complete_move_set.append(moves)
                        self.update_state([moves])
                    excess = np.sum(self.state - self.target_array, axis=0)
                    excess = excess[self.target_col_min:self.target_col_max + 1]
                    if (excess >= 0).all():
                        # solved
                        solved = True
                        break
            # do col compression
            for col_index in range(self.target_col_min, self.target_col_max + 1):
                moves = self.compress_col(self.state[:, col_index], self.target_array[:, col_index],
                                          self.helper_table[:, col_index])
                if len(moves) > 0:
                    while len(moves) > threshold:
                        # divide
                        z = 0
                        # print(moves)
                        while z != len(moves) and moves[z][2] - moves[z][0] > 0:
                            z += 1
                        # z is the first index where moving changes direction
                        if z >= threshold:
                            moves1 = moves[z - threshold:z]
                            moves = moves[:z - threshold] + moves[z:]
                        else:
                            moves1 = moves[z:z + threshold]
                            moves = moves[:z] + moves[z + threshold:]

                        # self.complete_move_set.append(moves)
                        self.complete_move_set.append(moves1)
                        self.update_state([moves1])
                    # else:
                    self.complete_move_set.append(moves)
                    self.update_state([moves])

        # if reconfig_round == self.reconfig_num:
        #     # last round, so also need to clean up reservoir
        #     for row_index in self.reservoir_rows_lower:
        #         # Here because this is the top few rows, we need to shift them left/rightwards.
        #         # For the Rb setup, we want to shift them towards H- so that the dropped atoms don't hit
        #         # the atoms in the array.
        #         atom_loc_in_array = np.nonzero(self.state[row_index]==1)[0]
        #         initial_indices = self.helper_table[row_index][atom_loc_in_array]
        #         moves = [initial_indices[i] + (row_index, -1, 'r') for i in range(len(initial_indices))]
        #         filtered_moves = list(filter(lambda x: x[0]!=x[2] or x[1] != x[3], moves))
        #         if len(filtered_moves) > 0:
        #             self.complete_move_set.append(filtered_moves)
        #             self.update_state([filtered_moves])
        #             # print(filtered_moves)
        #     for row_index in self.reservoir_rows_upper[::-1]:
        #         # Here we shift and drop down all the atoms starting from last row
        #         atom_loc_in_array = np.nonzero(self.state[row_index]==1)[0]
        #         initial_indices = self.helper_table[row_index][atom_loc_in_array]
        #         moves = [initial_indices[i] + (self.nrows, initial_indices[i][1],'c') for i in range(len(initial_indices))]
        #         filtered_moves = list(filter(lambda x: x[0]!=x[2] or x[1] != x[3], moves))
        #         if len(filtered_moves) > 0:
        #             self.complete_move_set.append(filtered_moves)
        #             self.update_state([filtered_moves])
        #             # print(filtered_moves)
        return counter

    def check_complete(self):
        if (self.state == self.target_array).all():
            return 1
        return 0

    def get_all_moves(self,atom_array):
        self.set_state(atom_array)
        self.generate_moves()
        return self.complete_move_set


def generate_full_array(initial_array_size, target_array_size, top_gap=1):
    l = np.ones(shape=(initial_array_size, initial_array_size)).astype(np.int32)
    bot_gap = (initial_array_size - target_array_size) - top_gap
    for i in range(top_gap):
        l[i] = np.zeros(shape=(initial_array_size))
        for j in range(initial_array_size):
            l[j, i] = 0
    for i in range(bot_gap):
        l[-(i + 1)] = np.zeros(shape=(initial_array_size))
        for j in range(initial_array_size):
            l[j, -(i + 1)] = 0
    return l


def kagome(initial_array_size, target_array_size, top_gap=1, odd=True):  # for odd number target only
    l = generate_full_array(initial_array_size, target_array_size, top_gap)
    for k in range(target_array_size // 2):
        for m in range(target_array_size // 2):
            if odd:
                l[2 * k + top_gap + 1, 2 * m + top_gap + 1] = 0
            else:
                l[2 * k + top_gap, 2 * m + top_gap] = 0
    return l


def honeycomb(initial_array_size, target_array_size, top_gap=1):
    l = generate_full_array(initial_array_size, target_array_size, top_gap)
    for i in range(target_array_size):
        for j in range(target_array_size):
            if not (i + j) % 3:
                l[i + top_gap, j + top_gap] = 0
    return l


def defect_free(initial_array_size, target_array_size, top_gap=1):
    l = generate_full_array(initial_array_size, target_array_size, top_gap)
    for i in range(target_array_size):
        for j in range(target_array_size):
            l[i + top_gap, j + top_gap] = 1
    return l


def defect_free_lukin(target_array_size):
    x = [[1 for _ in range(target_array_size)], [0 for _ in range(target_array_size)]]
    target_array = []
    for _ in range(target_array_size):
        target_array.extend(x.copy())
    return np.array(target_array)



def main(state: np.ndarray):
    # capture_time = 60*1e-3 # for each capture and release in ms
    # move_time = 35*1e-3 # in ms




    capture_time = 15 * 1e-3  # for each capture and release in ms
    move_time = 89.333333 * 1e-3  # in ms
    # target_array = kagome(20,16,2,True)
    # target_array = honeycomb(20,15,2)
    import math
    # target_array = defect_free(12,8,2)
    all_time = []
    all_time_std = []
    all_move = []
    all_move_std = []
    # target_array = defect_free_lukin(i)
    # target_array = np.array([[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]])

    target_array = np.array([[0,0,0,0],
                             [0,1,1,0],
                             [0,0,0,0],
                             [0,0,0,0]])

    # print(target_array)
    amt = ArbitraryMultipleTweezersMoveCalc(target_array.shape[0], target_array.shape[1], 1, 2, target_array,
                                            capture_time, move_time, 1)
    # state = np.array([[0,0,0],
    #                          [0,0,1],
    #                          [0,0,0]])

    complete_moves = amt.get_all_moves(state)
    print(complete_moves)
    return complete_moves
if __name__ == "__main__":

    state_array = np.array([[0,1,0,0],
                             [0,1,0,1],
                             [0,1,0,1],
                             [1,0,0,1]])
    # state_array = np.array([[0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0],
    #                          [0,0,0,1,0,0,0,1,0,0,0,0,0,0,0,0],
    #                          [0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    #                          [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]])
    

    moves = main(state_array)
    for i in range(len(moves)):
        for j in range(len(moves[i])):
                state_array[moves[i][j][0],moves[i][j][1]] = 0
                state_array[moves[i][j][2],moves[i][j][3]] = 1
    print(state_array)
