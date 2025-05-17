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




def q_learning(source,destination,bw, num_epoch, gamma=0.8, epsilon=0.05, alpha=0.1, visualize=True, save_video=False):
    print("-" * 20)
    print("q_learning begins ...")
    imgs = []  # useful for gif/video generation
    len_of_paths = []
    # init all q(s,a)
    q = np.zeros((num_nodes, num_nodes))  # num_states * num_actions
    for i in range(1, num_epoch + 1):
        s_cur = source
        path = [s_cur]
        num_of_hops = 0
        len_of_path = 0
        while True:
            s_next = epsilon_greedy(s_cur, q, epsilon=epsilon)
            # greedy policy
            s_next_next = epsilon_greedy(s_next, q, epsilon=-0.2)  # epsilon<0, greedy policy
            # update q

            #print(s_next)
            minHop = find_min_hop_for_current_as(all_transactions,s_cur,s_next,bw)
            if minHop == -1:
                #return -1,-1
                hop =9999
            else:
                hop = minHop.Hop
            #print("min hop olan transaction")
            #print(minHop)
            #print("------------------------------------------")
            reward = -D[s_cur][s_next] - hop
            delta = reward + gamma * q[s_next, s_next_next] - q[s_cur, s_next]
            q[s_cur, s_next] = q[s_cur, s_next] + alpha * delta
            # update current state
            s_cur = s_next
            len_of_path += -reward
            path.append(s_cur)
            num_of_hops += hop
            if s_cur == destination:
                break
        len_of_paths.append(len_of_path)

    strs = "best path for node {} to node {}: ".format(source,destination)
    strs += "->".join([str(i) for i in path])
    #print(strs)
    #print(f"total number of hops: {num_of_hops}")
    return num_of_hops,path

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
                
                all_transaction = Transactions(PreviousAS, CurrentAS, NextAS, Bandwidth, Delay, Hop, Full_Path)
                all_transactions.append(all_transaction)
    return all_transactions

def find_current_as(all_transactions, value,bw):
    return [path for path in all_transactions if path.CurrentAS == value and path.Bandwidth >= bw]


def find_min_hop_for_current_as(all_transactions,currenAS, nextAS,bw):


    result= find_current_as(all_transactions,currenAS,bw)
    #print("CurrentAS  olan nesneler:")
    #for path in result:
    #    print(path)
    #print("------------------------------------------")
    #print(nextAS)
    current_as_paths = [path for path in result if path.NextAS == nextAS]
    # Eğer filtrelenmiş liste boşsa, None döndür
    if not current_as_paths:
        current_as_paths = [path for path in result if path.PreviousAS == nextAS]
        if not current_as_paths:
            return -1
    
    # Hop değeri en küçük olan nesneyi bul
    min_hop_path = min(current_as_paths, key=lambda path: path.Hop)
    return min_hop_path

def write_to_file(numofNodes,bw, num_of_hops, path ,execution_time, ):
    with open(f"result.txt", 'a') as file:
        # Başlık sadece ilk satırda yazılacak
        if file.tell() == 0:
            file.write("Num of Nodes\tBW\tNum of Hops\tPath\tExecution Time (seconds)\n")
        file.write(f"{numofNodes}\t{bw}\t{num_of_hops}\t{path}\t{execution_time}\n")


if __name__ == '__main__':

    parser = ArgumentParser()
    parser.add_argument("-s", "--solution", help="select the solution", type=str, default="value_iteration")
    args = parser.parse_args()
    solution = args.solution
    solution = "q-learning"

    with open("result.txt", "w") as dosya:
         dosya.write("Num of Nodes\tBW\tNum of Hops\tPath\tExecution Time (seconds)\n")

    # Komşuluk matrislerinin bulunduğu tek metin dosyasının yolu
    file_path = './network/adjacency_14_0_1_2_updated.txt'
    # Metinden matrisleri ayır
    matrices = read_matrices(file_path)
    #print(matrices)
    D = matrices
    
    num_nodes = len(D)

    number = [5, 6, 7, 8, 9, 10]
    # Döngü ile dizi içindeki her bir sayıyı okuma
    for i in number:
        #read transaction
        #transaction
        file_path = f"./transactions/transactions_nsfnet_{i}nodes.txt"
        all_transactions = read_transactions(file_path)
        #requests
        req_file = f"requests_nsfnet_{i}nodes.txt"
        with open(f"./requests/{req_file}", 'r') as file:
            headers = file.readline().strip().split('\t')
            for line in file:
                # Satırları tab karakterlerine göre ayıralım ve gerekli bilgileri alalım
                source_as, destination_as, bandwidth = line.strip().split('\t')
                #print(f"Source AS: {source_as}, Destination AS: {destination_as}, Bandwidth: {bandwidth}")
                # Belirtilen sayıları içeren bir dizi
                bwDemand = [1, 5, 10, 15, 20, 25]
                #bwDemand = [1]
                # Döngü ile dizi içindeki her bir sayıyı okuma
                for bw in bwDemand:
                    start_time = time.time()
                    num_of_hops,path = q_learning(int(source_as), int(destination_as),bw, num_epoch=100, gamma=0.8, epsilon=0.05, alpha=0.1, visualize=True, save_video=True)
                    end_time = time.time()
                    # Geçen süreyi hesaplayın
                    execution_time = end_time - start_time
                    #print(f"Run Time:{execution_time}")
                    write_to_file(i,bw, num_of_hops, path ,execution_time)
                    #print()