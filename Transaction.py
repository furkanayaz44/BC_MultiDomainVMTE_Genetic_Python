class Transaction:
    transactionID = 0  # class-level variable

    def __init__(self, as_no, pathlet_id):
        Transaction.transactionID += 1
        self.txID = Transaction.transactionID
        self.asNo = as_no
        self.pathletID = pathlet_id
        self.minBandwidth = 0.0
        self.maxDelay = 0.0
        self.reliability = 0.0
        self.numOfHops = 0
        self.fullpath = []
        self.ingress = ""
        self.egress = ""
        self.status = True

    def getTransactionID(self):
        return self.txID

    def getTotalTransactionSize(self):
        return Transaction.transactionID

    def getASNo(self):
        return self.asNo

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
        self.numOfHops = len(self.fullpath) - 1

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
