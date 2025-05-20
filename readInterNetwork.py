class InterNetworkReader:
    def __init__(self, file_path):
        self.adjacency_matrix = []
        self.bandwidth_matrix = []
        self.delay_matrix = []
        self.reliability_matrix = []
        self.spectrum_matrix = []

        self._parse_file(file_path)

    def _parse_file(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read().strip()
        blocks = content.split('\n\n')

        self.adjacency_matrix = self._parse_matrix(blocks[0])
        self.bandwidth_demand = self._parse_matrix(blocks[1])
        self.delay_matrix = self._parse_matrix(blocks[2])
        self.reliability_matrix = self._parse_matrix(blocks[3])
        self.spectrum_matrix = self._parse_matrix(blocks[4])

    def _parse_matrix(self, block):
        return [list(map(int, line.strip().split('\t'))) for line in block.strip().split('\n')]

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
