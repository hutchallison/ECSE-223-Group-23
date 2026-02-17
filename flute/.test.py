#!/usr/bin/python3

import math
import numpy as np

def bhatta_distance(mean1, cov1, mean2, cov2):
	"""
	Calculates the Bhattacharyya distance between two 3d gaussian 
	distributions given their means and covariances. Using formula
	from Wikipedia Bhattacharyya page.

	Parameters:
		mean1: 1x3 numpy array with 3 mean values for each axis of data 
			from distribution 1

		cov1: 3x3 numpy array with the 3 covariance matrices for each 
			axis of data from distribution 1/usr/bin/python3
			
		mean2: 1x3 numpy array with 3 mean values for each axis of data 
			from distribution 2

		cov2: 3x3 numpy array with the 3 covariance matrices for each 
			axis of data from distribution 2 

	Returns:
		The Bhattacharyya distance between the two distributions float
	"""

	mean_difference = np.subtract(mean1, mean2)
	
	mean_difference_transpose = mean_difference.T
	
	cov_sum = np.divide(np.add(cov1, cov2), 2)
	
	inverse_cov_sum = np.linalg.inv(cov_sum)
	
	term_1 = 0.125 * mean_difference @ inverse_cov_sum @ mean_difference_transpose
	
	det_cov_sum = np.linalg.det(cov_sum)
	
	det_cov1 = np.linalg.det(cov1)
	
	det_cov2 = np.linalg.det(cov2)

	term_2 = 0.5*math.log(det_cov_sum / math.sqrt(det_cov1*det_cov2))

	bhatta_dist = term_1 + term_2
	
	return bhatta_dist

a = np.array([1,2,3])
b = np.array([[1,0.2,0],[0.2,1,0.1],[0,0.1,1]])
c = np.array([2,1,4])
d = np.array([[1.5,0.1,0],[0.1,1.2,0.2],[0,0.2,1.1]])
print(bhatta_distance(a,b,c,d))

