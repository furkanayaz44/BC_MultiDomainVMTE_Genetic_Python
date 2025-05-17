import string
from argparse import ArgumentParser
import random
import imageio
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from Transactions import Transactions
from read_matrices import read_matrices
import time
import os

from TimeCalculator import TimeCalculator
random.seed(100)
np.random.seed(50)

def cal_distance(path):
    dis = 0
    for i in range(len(path) - 1):
        dis += D[path[i]][path[i + 1]]
    return dis


def get_best_actions(D, states):
    best_actions = []
    for node in range(1, num_nodes):
        actions = [(idx, states[idx]) for idx, weight in enumerate(D[node]) if weight > 0]
        actions, scores = zip(*actions)
        best_actions.append((node, actions[scores.index(max(scores))]))
    return best_actions


def print_best_actions(best_actions):
    best_actions_info = ["{}->{}".format(item[0], item[1]) for item in best_actions]
    return ", ".join(best_actions_info)


def epsilon_greedy(s_curr, q, epsilon):
    # find the potential next states(actions) for current state
    potential_next_states = np.where(np.array(D[s_curr]) > 0)[0]
    if random.random() > epsilon:  # greedy
        q_of_next_states = q[s_curr][potential_next_states]
        s_next = potential_next_states[np.argmax(q_of_next_states)]
    else:  # random select
        s_next = random.choice(potential_next_states)
    return s_next


def q_learning_shortest_path(M, source,destination,bw, gamma=0.8, alpha=0.1, epsilon=0.02, num_episodes=500):

    # Q tablosunu başlat
    Q = np.zeros_like(M, dtype=float)

    def choose_action(state):
        if np.random.rand() < epsilon:
            return np.random.choice(np.where(M[state] > 0)[0])
        else:
            return np.argmax(Q[state])

    def update_q_table(state, action, reward, next_state):
        best_next_action = np.argmax(Q[next_state])
        Q[state, action] += alpha * (reward + gamma * Q[next_state, best_next_action] - Q[state, action])

    # Eğitim döngüsü
    for _ in range(num_episodes):
        current_state = source
        while current_state != destination:
            action = choose_action(current_state)
            next_state = action
            #reward = 1 if next_state == target else 0

            minHop = find_min_hop_for_current_as(all_transactions,current_state,next_state,bw)
            if minHop == -1:
                #return -1,-1
                hop =9999
            else:
                hop = minHop.Hop
            
            if next_state == destination:
                reward =  -M[current_state, next_state]  - hop
            else:
                reward = -M[current_state, next_state]  - hop

            update_q_table(current_state, action, reward, next_state)
            current_state = next_state

    # En kısa yolun belirlenmesi
    path = [source]
    current_state = source
    totalDelay = 0
    totalHop = 0
    count = 0
    while current_state != destination and count < len(M):
        next_state = np.argmax(Q[current_state])
        path.append(next_state)
        minHop = find_min_hop_for_current_as(all_transactions,current_state,next_state,bw)
        if(minHop != -1):
            totalDelay += minHop.Delay
            totalHop += minHop.Hop
            current_state = next_state
        else:
             return None,None,None
        count+=1
    return path, totalDelay, totalHop

def read_transactions(file_path):
    all_transactions = []
    with open(file_path, 'r') as file:
        # İlk satırı oku ve atla (başlık satırı)
        headers = file.readline().strip().split('\t')
        
        # Geri kalan satırları işle
        for line in file:
            parts = line.strip().split('\t')
            if len(parts) == 7:
                PreviousAS = int(parts[0])
                CurrentAS = int(parts[1])
                NextAS = int(parts[2])
                Bandwidth = float(parts[3])
                Delay = float(parts[4])
                Hop = int(parts[5])
                Full_Path = parts[6]
                # reliability = #5th matrix index 
                
                all_transaction = Transactions(PreviousAS, CurrentAS, NextAS, Bandwidth, Delay, Hop, Full_Path)
                all_transactions.append(all_transaction)
    return all_transactions

def find_current_as(all_transactions, value,bw):
    return [path for path in all_transactions if path.CurrentAS == value and path.Bandwidth >= bw]


def find_min_hop_for_current_as(all_transactions,currenAS, nextAS,bw):

    result= find_current_as(all_transactions,currenAS,bw)
    current_as_paths = [path for path in result if path.NextAS == nextAS]
    # Eğer filtrelenmiş liste boşsa, None döndür
    if not current_as_paths:
        current_as_paths = [path for path in result if path.PreviousAS == nextAS]
        if not current_as_paths:
            return -1
    
    # Hop değeri en küçük olan nesneyi bul
    min_hop_path = min(current_as_paths, key=lambda path: path.Hop)
    return min_hop_path
    #random_path = random.choice(current_as_paths)
    #return random_path
   

def write_to_file_rl(numofNodes, bw, totalDelay, num_of_hops, path, execution_time,network):
    with open(f"results_d/rl_result_bw_"+network+".txt", 'a') as file:
        # Başlık sadece ilk satırda yazılacak
        if file.tell() == 0:
            file.write("Num of Nodes\tBW\tTotalDelay\tNum of Hops\tPath\tExecution Time (seconds)\n")
        file.write(f"{numofNodes}\t{bw}\t{totalDelay}\t{num_of_hops}\t{path}\t{execution_time}\n")


def write_to_file_hra(numofNodes, bw, totalDelay, num_of_hops, path, fs_hra,network):
    with open(f"results_d/hra_result_bw_"+network+".txt", 'a') as file:
        # Başlık sadece ilk satırda yazılacak
        if file.tell() == 0:
            file.write("Num of Nodes\tBW\tTotalDelay\tNum of Hops\tPath\tExecution Time (seconds)\n")
        file.write(f"{numofNodes}\t{bw}\t{totalDelay}\t{num_of_hops}\t{path}\t{fs_hra}\n")


def write_to_file_dra(numofNodes, bw, totalDelay, num_of_hops, path, fs_dra,network):
    with open(f"results_d/dra_result_bw_"+network+".txt", 'a') as file:
        # Başlık sadece ilk satırda yazılacak
        if file.tell() == 0:
            file.write("Num of Nodes\tBW\tTotalDelay\tNum of Hops\tPath\tExecution Time (seconds)\n")
        file.write(f"{numofNodes}\t{bw}\t{totalDelay}\t{num_of_hops}\t{path}\t{fs_dra}\n")






if __name__ == '__main__':
    
    #for nsfnet --> networkType = 0
    #for usnet --> networkType = 1
    networkType = 0 

    if(networkType == 0):
        network = 'NSFNET'
        adjacency= 'adjacency_14_0_1_2_updated.txt'
        transactionsType = 'nsfnet'
    else:
        network = 'USNET'
        adjacency= 'adjacency_24_0_1_1_updated.txt'
        transactionsType = 'usnet'

    parser = ArgumentParser()
    parser.add_argument("-s", "--solution", help="select the solution", type=str, default="value_iteration")
    args = parser.parse_args()
    solution = args.solution
    solution = "q-learning"

    # Komşuluk matrislerinin bulunduğu tek metin dosyasının yolu
    cur_path = os.getcwd()
    file_path = os.path.join(cur_path, network, 'network', adjacency)
    # Metinden matrisleri ayır
    matrices = read_matrices(file_path)
    #print(matrices)
    D = matrices
    
    num_nodes = len(D)

    number = [5, 6, 7, 8, 9, 10]
    # Döngü ile dizi içindeki her bir sayıyı okuma
    for i in number:
        #read transaction
        transactions = f"transactions_" + transactionsType + "_" + str(i) + "nodes.txt"  
 
        file_path = os.path.join(cur_path, network, 'transactions', transactions)
        all_transactions = read_transactions(file_path)
        #requests
        reqs = f"requests_" + transactionsType + "_" + str(i) + "nodes.txt" 
        req_path = os.path.join(cur_path, network, 'requests', reqs)
        with open(req_path, 'r') as file:
            headers = file.readline().strip().split('\t')
            for line in file:
                # Satırları tab karakterlerine göre ayıralım ve gerekli bilgileri alalım
                source_as, destination_as, bandwidth = line.strip().split('\t')

                # Belirtilen sayıları içeren bir dizi
                bwDemand = [1, 5, 10, 15, 20, 25]
                # Döngü ile dizi içindeki her bir sayıyı okuma
                for bw in bwDemand:
                    print("code running")
                    print(transactions+" ---" + reqs)
                    start_time = time.time()
                    pathRL, totalDelay,totalHop  = q_learning_shortest_path(D, int(source_as), int(destination_as), bw)
                    #num_of_hops, pathRL, total_delay = q_learning(int(source_as), int(destination_as), bw, num_epoch=100, gamma=0.8, epsilon=0.05, alpha=0.1, visualize=True, save_video=True)
                    end_time = time.time()
                    if(pathRL != None):
                        numOfController =len(pathRL)
                        execution_time = end_time - start_time
                        obj = TimeCalculator()
                        fs_hra = obj.get_fs_od(execution_time)
                        fs_dra = obj.get_fs_dcd(numOfController, execution_time)
                        write_to_file_rl(i, bw,totalDelay, totalHop, pathRL, execution_time, network)
                        write_to_file_hra(i, bw,totalDelay, totalHop, pathRL, fs_hra, network)
                        write_to_file_dra(i, bw,totalDelay, totalHop, pathRL, fs_dra, network)
                        #print()
                    else:
                        write_to_file_rl(i, bw,-1, -1, -1, -1, network)
                        write_to_file_hra(i, bw,-1, -1, -1, -1, network)
                        write_to_file_dra(i, bw,-1, -1, -1, -1, network)
