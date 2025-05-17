import numpy as np

def read_matrices(file_path):
    """
    Verilen dosya yolundaki metni okuyup içerisinde bulunan komşuluk matrislerini NumPy dizileri olarak döndüren fonksiyon.
    """
    matrices = []
    with open(file_path, 'r') as file:
        data = file.read().strip()  # Dosyayı oku ve baştaki ve sondaki boşlukları sil
        matrix_texts = data.split('\n\n')  # Matrisleri boşluklardan ayır
        for matrix_text in matrix_texts:
            rows = matrix_text.strip().split('\n')  # Satırları ayır
            matrix = []
            for row in rows:
                matrix.append(list(map(int, row.strip().split('\t'))))  # Satırdaki elemanları tab karakterinden ayır ve tamsayıya dönüştür
            matrices.append(np.array(matrix))  # Matrisi NumPy dizisine dönüştür ve listeye ekle
    for i, matrix in enumerate(matrices, 1):
        if i == 2:
            bwMatrix = matrix
    return bwMatrix



# Matrisleri yazdırma (isteğe bağlı)

