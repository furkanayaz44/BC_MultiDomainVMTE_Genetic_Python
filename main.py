
import networkx as nx
import os
import pandas as pd
from collections import defaultdict
import csv
import ast

from read_matrices_with_specific_types import read_matrices_with_specific_types
from vread_matrices_with_specific_types import vread_matrices_with_specific_types

from genetic import genetic_algorithm 

def main():
    file_path = "SN/senaryo1_erdos_renyi_n10_p0.5_copy1.txt"
    matrices = read_matrices_with_specific_types(file_path)

    # İlgili matrisleri 2D array olarak tut
    adjacencySubstrate = matrices.get('Adjacency Matrix:', [])
    bandwidthSubstrate = matrices.get('Bandwidth Matrix:', [])
    delaySubstrate = matrices.get('Delay Matrix:', [])
    reliabilitySubstrate = matrices.get('Reliability Matrix:', [])
    cpuSubstrate = matrices.get('CPU:Node Number:Domain Number', [])
    # print("Adjacency Matrix:", adjacencySubstrate)
    # print("Bandwidth Matrix:", bandwidthSubstrate)
    # print("Delay Matrix:", delaySubstrate)
    # print("Reliability Matrix:", reliabilitySubstrate)
    # print("CPU Matrix:", cpuSubstrate)

    #read vn
    directory_path = "VN/"
    all_files = os.listdir(directory_path)
    txt_files = [file for file in all_files if file.endswith('.txt')]



    for file_name in txt_files:
        file_path = os.path.join(directory_path, file_name)
        matrices = vread_matrices_with_specific_types(file_path)

        if not matrices:
            continue

    adjacencyVirtual = matrices['Adjacency Matrix:']
    bandwidthVirtual = matrices['Bandwidth Matrix:']
    delayVirtual = matrices['Delay Matrix:']
    reliabilityVirtual = matrices['Reliability Matrix:']
    cpuVirtual = matrices['CPU:Node Number:Domain Number']

    # print("Adjacency Matrix:", adjacencyVirtual)
    # print("Bandwidth Matrix:", bandwidthVirtual)
    # print("Delay Matrix:", delayVirtual)
    # print("Reliability Matrix:", reliabilityVirtual)
    # print("CPU Matrix:", cpuVirtual)
   
    candidateDomains = getCandidateDomainNumber(cpuVirtual)
    #print(candidateDomains)

    population_size = 6  # Popülasyon büyüklüğü
    iterations = 50  # Maksimum iterasyon sayısı

    vn_count = len(cpuVirtual)
    best_chromosome, best_fitness = genetic_algorithm(vn_count, candidateDomains, population_size, iterations)
    print("Best Chromosome:", best_chromosome)
    print("Best Fitness:", best_fitness)



#bu metot isteklerdeki aday düğümleri getiriyor genetik için kullanıldı
def getCandidateDomainNumber(cpu_matrix):#parametre virtualCpu kısmı
    separate_elements = []
    for row in cpu_matrix:
        row_elements = []
        for element in row:
            if isinstance(element, list):
                row_elements.extend(element)
        separate_elements.append(row_elements)
    return separate_elements



if __name__ == "__main__":
    main()