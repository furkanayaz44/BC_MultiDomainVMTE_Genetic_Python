class Transaction:
    transactionID = 0  # class-level variable

    def __init__(self, TransactionId,ASId,Ingress,Egress,PathletId,Bandwidth,Delay,Reliability,Status,Full_Path):
        self.TransactionId = TransactionId
        self.ASId = ASId
        self.pathletID = PathletId
        self.minBandwidth = Bandwidth
        self.maxDelay = Delay
        self.reliability = Reliability
        self.numOfHops = 0
        self.fullpath = Full_Path
        self.ingress = Ingress
        self.egress = Egress
        self.status = True
        self.setNumOfHops = self.setNumOfHops()


    def find_current_as(self,all_transactions, value,bw):
        return [path for path in all_transactions if path.CurrentAS == value and path.Bandwidth >= bw]

    def find_min_hop_for_current_as(self,all_transactions,currenAS, nextAS,bw):

        result= self.find_current_as(all_transactions,currenAS,bw)
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

    def getTransactionID(self):
        return self.txID

    def getTotalTransactionSize(self):
        return Transaction.transactionID

    def getASId(self):
        return self.ASId

    def getPathletId(self):
        return str(self.pathletID)

    def setIngressNode(self, node):
        self.ingress = node

    def getIngressNode(self):
        return self.ingress

    def setEgressNode(self, node):
        self.egress = node

    def getEgressNode(self):
        return self.egress

    def getStartNode(self):
        return self.fullpath[0]

    def getEndNode(self):
        return self.fullpath[-1]

    def setBandwidth(self, bandwidth):
        self.minBandwidth = bandwidth

    def getMinBandwidth(self):
        return self.minBandwidth

    def setDelay(self, delay):
        self.maxDelay = delay

    def getMaxDelay(self):
        return self.maxDelay

    def setReliability(self, reliability):
        self.reliability = reliability

    def getReliability(self):
        return self.reliability

    def setFullPath(self, path):
        if path and path != "[]":
            temp = path.split(",")

            for i in range(len(temp)):
                value = ""
                if i == 0:
                    value = temp[i][1:].strip()
                    if len(value) > 3:
                        value = value[len(value) // 2:]
                    value = f"{int(value):03d}"
                    self.setIngressNode(value)
                elif i == len(temp) - 1:
                    value = temp[i][:-1].strip()
                    if len(value) > 3:
                        value = value[len(value) // 2:]
                    value = f"{int(value):03d}"
                    self.setEgressNode(value)
                else:
                    value = temp[i].strip()
                    if len(value) >= 3:
                        value = value[len(value) // 2:]
                    value = f"{int(value):03d}"
                self.fullpath.append(value)

    def setNumOfHops(self):
        self.numOfHops = len([int(num) for num in self.fullpath.strip('[]').split(',')])

    def getNumOfHops(self):
        return self.numOfHops

    def setFullPathForBorder(self, path):
        self.fullpath = path

    def getFullPath(self):
        return self.fullpath

    def getFullPathNodeList(self):
        return [int(node) for node in self.fullpath]

    def setStatus(self, stat):
        self.status = stat

    def getStatus(self):
        return self.status
