import os
import re

class IntraNetworkReader:
    def __init__(self, file_name=None):
        self.file_name = file_name
        self.adjacency_matrix = []
        self.bandwidth_matrix = []
        self.delay_matrix = []
        self.reliability_matrix = []
        self.spectrum_matrix = []
        self.cpu_matrix = []

    def load_from_file(self, file_path):
        self.file_name = os.path.basename(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        blocks = re.split(r"\n\s*\n", content)

        if len(blocks) < 6:
            raise ValueError(
                f"{file_path} içinde 6 blok matris bekleniyordu ama {len(blocks)} bulundu."
            )

        self.adjacency_matrix   = self._parse_block(blocks[0])
        self.bandwidth_matrix   = self._parse_block(blocks[1])
        self.delay_matrix       = self._parse_block(blocks[2])
        self.reliability_matrix = self._parse_block(blocks[3])
        self.spectrum_matrix    = self._parse_block(blocks[4])
        self.cpu_matrix         = self._parse_block(blocks[5])

        return self

    def _parse_block(self, block):
        # Tab veya boşluk ile ayrılmış sayıları okuma
        return [list(map(int, re.split(r"\s+", line.strip())))
                for line in block.strip().splitlines()
                if line.strip()]

    def get_adjacency_matrix(self):
        return self.adjacency_matrix

    def get_bandwidth_matrix(self):
        return self.bandwidth_matrix

    def get_delay_matrix(self):
        return self.delay_matrix

    def get_reliability_matrix(self):
        return self.reliability_matrix

    def get_spectrum_matrix(self):
        return self.spectrum_matrix

    #butun intra arasında rastgele alıyordu degisti
    def load_all_topologies_with_node_count(folder_path, target_node_count):
   
        topologies = []

        if not os.path.isdir(folder_path):
            raise FileNotFoundError(f"Klasör bulunamadı: {folder_path}")

        for fname in sorted(os.listdir(folder_path)):
            # En baştaki sayıyı çek
            match = re.match(r"[^0-9]*([0-9]+)_", fname)
            if match and int(match.group(1)) == target_node_count:
                full_path = os.path.join(folder_path, fname)

                if not os.path.isfile(full_path):
                    continue

                topo = IntraNetworkReader().load_from_file(full_path)
                topologies.append(topo)

        return topologies
    
    #bu kod var olan text den gelen kullanılan intraları alıyor
    def load_intra_topology(folder_path, intraNameList):
        topologies = []

        if not os.path.isdir(folder_path):
            raise FileNotFoundError(f"Klasör bulunamadı: {folder_path}")
        
        for fname in intraNameList:            
            full_path = os.path.join(folder_path, fname)
            if not os.path.isfile(full_path):
                continue
            topo = IntraNetworkReader().load_from_file(full_path)
            topologies.append(topo)

        return topologies
