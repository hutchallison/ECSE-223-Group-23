#!/usr/bin/python3

import numpy as np

def create_gaussian(data):
    """
    Fits 3d data to a 3d gaussian distribution
    
    Parameters:
        data: A 3d numpy array with each row being an axis of data

    Returns:
        mean: A 1x3 numpy array with the mean value of each row of data
        cov: A 3x3 numpy array with the covarience matrix 1x3 of each row of data
    """
    mean = np.mean(data, axis = 1) #finds the mean of each row of data  
    cov = np.cov(data) #finds the covariance of each row of data
    return mean, cov
