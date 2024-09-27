import numpy as np
from yroots.IntervalChecks import constant_term_check, quadratic_check, IntervalData
from yroots.old_code.OldIntervalChecks import full_quad_check, full_cubic_check, curvature_check, linear_check
from yroots.polynomial import MultiCheb,MultiPower
import itertools
from scipy import linalg as la

macheps = 2.220446049250313e-16

def base_quadratic_check(test_coeff,tol):
    """Slow nd-quadratic check to test against. """
    #get the dimension and make sure the coeff tensor has all the right
    # quadratic coeff spots, set to zero if necessary
    dim = test_coeff.ndim
    interval_data = IntervalData(-np.ones(dim), np.ones(dim), [])
    intervals = interval_data.get_subintervals(interval_data.a, interval_data.b, [], tol, False)
    padding = [(0,max(0,3-i)) for i in test_coeff.shape]
    test_coeff = np.pad(test_coeff.copy(), padding, mode='constant')

    #Possible extrema of qudaratic part are where D_xk = 0 for some subset of the variables xk
    # with the other variables are fixed to a boundary value
    #Dxk = c[0,...,0,1,0,...0] (k-spot is 1) + 4c[0,...,0,2,0,...0] xk (k-spot is 2)
    #       + \Sum_{j\neq k} xj c[0,...,0,1,0,...,0,1,0,...0] (k and j spot are 1)
    #This gives a symmetric system of equations AX+B = 0
    #We will fix different columns of X each time, resulting in slightly different
    #systems, but storing A and B now will be helpful later

    #pull out coefficients we care about
    quad_coeff = np.zeros([3]*dim)
    A = np.zeros([dim,dim])
    B = np.zeros(dim)
    for spot in itertools.product(np.arange(3),repeat=dim):
        if np.sum(spot) < 3:
            spot_array = np.array(spot)
            if np.sum(spot_array != 0) == 2:
                #coef of cross terms
                i,j = np.where(spot_array != 0)[0]
                A[i,j] = test_coeff[spot].copy()
                A[j,i] = test_coeff[spot].copy()
            elif np.any(spot_array == 2):
                #coef of pure quadratic terms
                i = np.where(spot_array != 0)[0][0]
                A[i,i] = 4*test_coeff[spot].copy()
            elif np.any(spot_array == 1):
                #coef of linear terms
                i = np.where(spot_array != 0)[0][0]
                B[i] = test_coeff[spot].copy()
            quad_coeff[spot] = test_coeff[spot]
            test_coeff[spot] = 0

    #create a poly object for evaluations
    quad_poly = MultiCheb(quad_coeff)

    #The sum of the absolute values of everything else
    other_sum = np.sum(np.abs(test_coeff))

    def powerset(iterable):
        "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        s = list(iterable)
        return itertools.chain.from_iterable(itertools.combinations(s, r)\
                                                     for r in range(len(s)+1))
    mask = []
    for interval_num, interval in enumerate(intervals):

        extreme_points = []
        for fixed in powerset(np.arange(dim)):
            fixed = np.array(fixed)
            if len(fixed) == 0:
                #fix no vars--> interior
                if np.linalg.matrix_rank(A) < A.shape[0]:
                    #no interior critical point
                    continue
                X = la.solve(A, -B, assume_a='sym')
                #make sure it's in the domain
                if np.all([interval[0][i] <= X[i] <= interval[1][i] for i in range(dim)]):
                    extreme_points.append(quad_poly(X))
            elif len(fixed) == dim:
                #fix all variables--> corners
                for corner in itertools.product([0,1],repeat=dim):
                    #j picks if upper/lower bound. i is which var
                    extreme_points.append(quad_poly([interval[j][i] for i,j in enumerate(corner)]))
            else:
                #fixed some variables --> "sides"
                #we only care about the equations from the unfixed variables
                unfixed = np.delete(np.arange(dim), fixed)
                A_ = A[unfixed][:,unfixed]
                if np.linalg.matrix_rank(A_) < A_.shape[0]:
                    #no solutions
                    continue
                fixed_A = A[unfixed][:,fixed]
                B_ = B[unfixed]

                for side in itertools.product([0,1],repeat=len(fixed)):
                    X0 = np.array([interval[j][i] for i,j in enumerate(side)])
                    X_ = la.solve(A_, -B_-fixed_A@X0, assume_a='sym')
                    X = np.zeros(dim)
                    X[fixed] = X0
                    X[unfixed] = X_
                    if np.all([interval[0][i] <= X[i] <= interval[1][i] for i in range(dim)]):
                        extreme_points.append(quad_poly(X))

        #No root if min(extreme_points) > (other_sum + tol)
        # OR max(extreme_points) < -(other_sum+tol)
        #Logical negation gives the boolean we want
        mask.append(np.min(extreme_points) < (other_sum + tol)
                and np.max(extreme_points) > -(other_sum+tol))

    return mask

def test_zero_check2D():
    #curvature_check was causing import errors so it's not included...
    interval_checks = [constant_term_check,full_quad_check, full_cubic_check]
    a = -np.ones(2)
    b = np.ones(2)
    interval_data = IntervalData(a, b, [])
    tol = 1.e-4
    interval_checks.extend([lambda x, tol: ~quadratic_check(x, interval_data.mask, tol, interval_data.RAND, np.array([(a, b)] * 4))[0][0]])

    test_cases =[
    np.array([
    [ 100,  2, -2, -1],
    [ 2,  2,  1,  0],
    [-1,  1,  0,  0],
    [ 1,  0,  0,  0]
    ]),
    np.array([
    [ 6.5,  2, -2, -1],
    [ 2,  2,  1,  0],
    [-1,  1,  0,  0],
    [ 1,  0,  0,  0]
    ]),
    np.array([
    [1.019, .2,   .5],
    [0.2,   .001, 0],
    [0.5,  0,     0],
    ]),
    np.array([
    [-1.3, .2,   0.5],
    [.2,   .001, 0],
    [.5,  0,     0],
    ]),
    np.array([
    [-1.6, .2,   .5, .1],
    [.2,   .001, .1, 0],
    [0.5,  .1,    0, 0],
    [0.1,   0,    0, 0]
    ])]
    correct_results = [False,True,True,True,True,True]

    for method in interval_checks:
        for res,c in zip(correct_results,test_cases):
            assert res == method(c,tol)

def test_quadratic_check():
    #keep this updated with the deg_dim used in subdivision solve
    deg_dim = {1: 100, 2:20, 3:9, 4:9}
    num_tests_per_dim = 100
    tests_per_batch = num_tests_per_dim//2
    tol = 1.e-4
    for dim in deg_dim.keys():
        print(dim)
        deg = deg_dim[dim]
        interval_data = IntervalData(-np.ones(dim), np.ones(dim), [])
        subintervals = interval_data.get_subintervals(interval_data.a, interval_data.b, [], tol, False)
        _quadratic_check = lambda c, tol: ~quadratic_check(c, interval_data.mask, tol, interval_data.RAND, subintervals)
        np.random.seed(42)
        rand_test_cases = np.random.rand(*[tests_per_batch]+[deg]*dim)*2-1
        randn_test_cases = np.random.randn(*[tests_per_batch]+[deg]*dim)
        for c in rand_test_cases:
            assert np.allclose(base_quadratic_check(c,tol), _quadratic_check(c,tol).flatten())
        for c in randn_test_cases:
            assert np.allclose(base_quadratic_check(c,tol), _quadratic_check(c,tol).flatten())

def test_quadratic_check3D():
    #test 1
    a = np.array([-2.78150902e-05, -2.78150902e-05, -2.78150902e-05])
    b = np.array([4.19383023e-05, 4.19383023e-05, 4.19383023e-05])
    tol = macheps


if __name__ == "__main__":
    test_zero_check2D()
    test_quadratic_check()
