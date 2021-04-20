
# Calculate Cohen's Kappa and Krippendorff's Alpha for a given
# contingency matrix, given as a 2d array.
def calculate_agreement_coefs(contingency_mat):
    n = 0
    for i in range(len(contingency_mat)):
        for j in range(len(contingency_mat[0])):
            n += contingency_mat[i][j]
    if n == 0:
        return None
    p_o = 0
    for i in range(len(contingency_mat)):
        p_o += contingency_mat[i][i]
    p_o /= n

    marginal_col = [sum(x) for x in contingency_mat]
    marginal_row = [sum(x) for x in list(zip(*contingency_mat))]
    p_e_cohen = sum([a * b for a, b in zip(marginal_row, marginal_col)])/(n*n)
    kappa = (p_o - p_e_cohen) / (1-p_e_cohen)

    coincidence_mat = contingency_to_coincidence(contingency_mat)
    exp_distribution = [sum(x) for x in coincidence_mat]
    p_e_krippendorf = sum([a * (a-1) for a in exp_distribution])/(2*n*((2*n)-1))
    alpha = (p_o - p_e_krippendorf) / (1-p_e_krippendorf)

    return {'observed_agreement': p_o, 'kappa': kappa, 'alpha': alpha}


def contingency_to_coincidence(contingency_mat):
    transposed_mat = [list(x) for x in zip(*contingency_mat)]
    #coincidence_mat = [row[:] for row in contingency_mat]
    coincidence_mat = [[0] * len(contingency_mat) for i in range(len(contingency_mat))]
    for i in range(len(contingency_mat)):
        for j in range(len(contingency_mat[0])):
            coincidence_mat[i][j] = contingency_mat[i][j] + transposed_mat[i][j]
    return coincidence_mat
