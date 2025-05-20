def readInterNetwork(text):

    matrices = {
        'Adjacency Matrix': [],
        'Bandwidth Matrix': [],
        'Delay Matrix': [],
        'Reliability Matrix': [],
        'Spectrum Matrix': []
    }

    matrix_names = list(matrices.keys())
    current_matrix_index = 0
    lines = text.strip().split('\n')

    for line in lines:
        if line.strip() == '':
            current_matrix_index += 1
            if current_matrix_index >= len(matrix_names):
                break  # Stop if we've extracted all matrices
        else:
            if current_matrix_index < len(matrix_names):
                matrices[matrix_names[current_matrix_index]].append(
                    [int(val) for val in line.split('\t')]
                )

    return matrices

def readIntraNetwork(text):

    matrices = {
        'Adjacency Matrix': [],
        'Bandwidth Matrix': [],
        'Delay Matrix': [],
        'Reliability Matrix': [],
        'CPU:Node Number:Domain Number': []
    }

    matrix_names = list(matrices.keys())
    current_matrix_index = 0
    lines = text.strip().split('\n')

    for line in lines:
        if line.strip() == '':
            current_matrix_index += 1
            if current_matrix_index >= len(matrix_names):
                break  # Stop if we've extracted all matrices
        else:
            if current_matrix_index < len(matrix_names):
                matrices[matrix_names[current_matrix_index]].append(
                    [int(val) for val in line.split('\t')]
                )

    return matrices