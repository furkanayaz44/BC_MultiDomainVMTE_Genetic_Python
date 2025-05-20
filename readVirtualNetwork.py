class VirtualNetworkRequest:
    def __init__(self, file_path):
        self.adjacency_matrix = []
        self.bandwidth_demand = []
        self.delay_matrix = []
        self.reliability_matrix = []
        self.cpu_ram_demand = []
        self.candidate_domains = []

        self._parse_file(file_path)

    def _parse_file(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read().strip()
        blocks = content.split('\n\n')

        self.adjacency_matrix = self._parse_matrix(blocks[0])
        self.bandwidth_demand = self._parse_matrix(blocks[1])
        self.delay_matrix = self._parse_matrix(blocks[2])
        self.reliability_matrix = self._parse_matrix(blocks[3])
        self.cpu_ram_demand = self._parse_matrix(blocks[4])
        self.candidate_domains = self._parse_matrix(blocks[5])

    def _parse_matrix(self, block):
        return [list(map(int, line.strip().split('\t'))) for line in block.strip().split('\n')]

    def get_bandwidth(self):
        """İlk bulunan sıfırdan farklı bant genişliği değerini döndür."""
        for i in range(len(self.bandwidth_demand)):
            for j in range(len(self.bandwidth_demand[i])):
                val = self.bandwidth_demand[i][j]
                if val != 0:
                    return val
        return None
