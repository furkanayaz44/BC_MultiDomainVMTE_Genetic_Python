from blockchain.Transaction import Transaction

def TransactionReader(file_path):
    all_transactions = []
    edgeRouter = []
    with open(file_path, 'r') as file:
        # İlk satırı oku ve atla (başlık satırı)
        headers = file.readline().strip().split('\t')
        
        # Geri kalan satırları işle
        for line in file:
            parts = line.strip().split('\t')
            if len(parts) == 10:
                TransactionId = int(parts[0])
                ASId = int(parts[1])
                Ingress = parts[2]
                Egress = parts[3]
                PathletId = int(parts[4])
                Bandwidth = int(float(parts[5]))
                Delay = int(float(parts[6]))
                rel = parts[7].replace(',', '.')
                Reliability = float(rel)
                Status = bool(parts[8])
                Full_Path = parts[9]
                

                edgeDomainIngress = int(Ingress[:3])
                edgeNodeIngress = int(Ingress[3:])

                edgeDomainEgress = int(Egress[:3])
                edgeNodeEgress = int(Egress[3:])


                all_transaction = Transaction(TransactionId,ASId,edgeDomainIngress,edgeNodeIngress,edgeDomainEgress,edgeNodeEgress,PathletId,Bandwidth,Delay,Reliability,Status,Full_Path)

                #print(all_transaction.getNumOfHops())
                if (all_transaction.getASId()) == -1:
                    edgeRouter.append(all_transaction)
                else:
                    all_transactions.append(all_transaction)
    return all_transactions,edgeRouter


   