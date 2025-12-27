import random
import sys
import os
import unittest

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from readFiles.TransactionReader import TransactionReader

networkType = "NSFNET"
folder = f"topologies/{networkType}"

class Test_TransactionReader(unittest.TestCase):
    def test_readIntraNetwork(self):
        folder_path = f"{folder}/transactions/"
        number = [5, 6, 7, 8, 9, 10]

        for file_name in os.listdir(folder_path):
           if file_name.endswith(".txt"):
               txt_name = os.path.splitext(file_name)[0]
               parts = txt_name.split('_')
               end_with = parts[-1]
               prefix = "_".join(parts[:-1])

        for i in number:
            #print(prefix)
            file_path = f"{prefix}_{i}.txt"
            print(file_path)
            full_path = os.path.join(folder_path, file_path)
            all_transactions = TransactionReader(full_path)
            ilk = all_transactions[0]
            print(ilk.fullpath)


if __name__ == '__main__':
    unittest.main()
