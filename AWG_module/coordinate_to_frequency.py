import spcm
from spcm import units
import numpy as np
import matplotlib.pyplot as plt
import random
import time
def convert_coordinate_to_frequency(start_frequency_on_row, start_frequency_on_col, end_frequency_on_row, end_frequency_on_col, start_site_on_row, start_site_on_col, end_site_on_row, end_site_on_col, atom_array):
    row_or_col_list = [] #determine if the col to be arranged or row
    single_frequency_list = []
    start_frequency_table = []
    end_frequency_table = []


    for i in range(len(atom_array)):
        end_frequency_list = [] #interval variable to complete the end_frequency_table
        start_frequency_list = []
        if atom_array[i][0][0] == atom_array[i][0][2]:  # (from_row, from_col, to_row, to_col)
            """"rearrange on row"""
            single_site = atom_array[i][0][0]
            row_or_col_list.append(True)  # False means to rearrange col, True means to rearrange row
            single_fre = start_frequency_on_row + (end_frequency_on_row - start_frequency_on_row) * (single_site - start_site_on_row) / (end_site_on_row - start_site_on_row)
            single_frequency_list.append(single_fre)
            for j in range(len(atom_array[i])):
                tp = atom_array[i][j] #extract the tuple
                start_site = tp[1]
                end_site = tp[3]
                start_fre = start_frequency_on_col + (end_frequency_on_col - start_frequency_on_col)*(start_site - start_site_on_col)/(end_site_on_col - start_site_on_col)
                end_fre = start_frequency_on_col + (end_frequency_on_col - start_frequency_on_col)*(end_site - start_site_on_col)/(end_site_on_col - start_site_on_col)
                start_frequency_list.append(start_fre)
                end_frequency_list.append(end_fre)
            start_frequency_table.append(start_frequency_list)
            end_frequency_table.append(end_frequency_list)

        else:
            """"rearrange on col"""
            single_site = atom_array[i][0][1]
            row_or_col_list.append(False)  # False means to rearrange col, True means to rearrange row
            single_fre = start_frequency_on_col + (end_frequency_on_col - start_frequency_on_col) * (single_site - start_site_on_col) / (end_site_on_col - start_site_on_col)
            single_frequency_list.append(single_fre)
            for j in range(len(atom_array[i])):
                tp = atom_array[i][j] #extract the tuple
                start_site = tp[0]
                end_site = tp[2]
                start_fre = start_frequency_on_row + (end_frequency_on_row - start_frequency_on_row)*(start_site - start_site_on_row)/(end_site_on_row - start_site_on_row)
                end_fre = start_frequency_on_row + (end_frequency_on_row - start_frequency_on_row)*(end_site - start_site_on_row)/(end_site_on_row - start_site_on_row)
                start_frequency_list.append(start_fre)
                end_frequency_list.append(end_fre)
            start_frequency_table.append(start_frequency_list)
            end_frequency_table.append(end_frequency_list)
    return row_or_col_list, single_frequency_list, start_frequency_table, end_frequency_table


# start_frequency_on_row = 90.75e6
# start_frequency_on_col = 111.25e6
# end_frequency_on_row = 111.25e6
# end_frequency_on_col = 90.75e6
# start_site_on_row = 0
# start_site_on_col = 0
# end_site_on_row = 9
# end_site_on_col = 9 #size of the array, now is 10*10
# a=[[(4, 2, 9, 2)]]
# a,b,c,d = convert_coordinate_to_frequency(start_frequency_on_row, start_frequency_on_col, end_frequency_on_row, end_frequency_on_col, start_site_on_row, start_site_on_col, end_site_on_row, end_site_on_col, a)
# print(d)