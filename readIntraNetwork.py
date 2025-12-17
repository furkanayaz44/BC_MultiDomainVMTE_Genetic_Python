import os
import re

class TopologyData:
    def __init__(self, file_name=None):
        self.file_name = file_name
        self.adjacency_matrix = []
        self.bandwidth_matrix = []
        self.delay_matrix = []
        self.reliability_matrix = []
        self.spectrum_matrix = []

    def load_from_file(self, file_path):
        self.file_name = os.path.basename(file_path)
        with open(file_path, 'r') as f:
            content = f.read().strip()

        blocks = content.split('\n\n')
        if len(blocks) < 5:
            raise ValueError(f"{file_path} içinde 5 blok matris yok.")

        self.adjacency_matrix = self._parse_block(blocks[0])
        self.bandwidth_matrix = self._parse_block(blocks[1])
        self.delay_matrix = self._parse_block(blocks[2])
        self.reliability_matrix = self._parse_block(blocks[3])
        self.spectrum_matrix = self._parse_block(blocks[4])

    def _parse_block(self, block):
        return [list(map(int, line.strip().split('\t'))) for line in block.strip().split('\n')]

def load_all_topologies_with_node_count(folder_path, target_node_count=5):
    """Sadece en başında `target_node_count` olan dosyaları yükle."""
    topologies = []
    for fname in sorted(os.listdir(folder_path)):
        # En baştaki sayıyı çek
        match = re.match(r"[^0-9]*([0-9]+)_", fname)
        if match and int(match.group(1)) == target_node_count:
            full_path = os.path.join(folder_path, fname)
            topo = TopologyData()
            topo.load_from_file(full_path)
            topologies.append(topo)
            print(f"{fname} dosyası yüklendi.")
    return topologies
