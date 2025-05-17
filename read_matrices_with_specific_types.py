def read_matrices_with_specific_types(file_path):
    matrices = {}
    current_matrix = []
    current_title = None

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()

            if not line:  # Boş satır: Matrisin sonu
                if current_matrix and current_title:
                    matrices[current_title] = current_matrix
                    current_matrix = []
                    current_title = None
            elif current_title is None:  # Başlık satırı
                current_title = line
            else:  # Matris içeriği
                values = line.split(':')
                row = [float(value) if current_title == "Reliability Matrix:" else int(value) for value in values]
                current_matrix.append(row)

        if current_matrix and current_title:
            matrices[current_title] = current_matrix

    return matrices