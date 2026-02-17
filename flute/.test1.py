#!/usr/bin/python3

import numpy as np

arr = np.array([[1,2,3],[4,5,6],[7,8,9]])

shifted_arr = np.roll(arr, -1, axis=1)

print(shifted_arr)
