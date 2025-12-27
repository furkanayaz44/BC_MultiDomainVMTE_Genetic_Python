from blockchain.Transaction import Transaction

def TransactionReader(file_path):
    all_transactions = []
    with open(file_path, 'r') as file:
        # İlk satırı oku ve atla (başlık satırı)
        headers = file.readline().strip().split('\t')
        
        # Geri kalan satırları işle
        for line in file:
            parts = line.strip().split('\t')
            if len(parts) == 10:
                TransactionId = int(parts[0])
                ASId = int(parts[1])
                Ingress = int(parts[2])
                Egress = int(parts[3])
                PathletId = int(parts[4])
                Bandwidth = int(float(parts[5]))
                Delay = int(float(parts[6]))
                rel = parts[7].replace(',', '.')
                Reliability = float(rel)
                Status = bool(parts[8])
                Full_Path = parts[9]
                

                all_transaction = Transaction(TransactionId,ASId,Ingress,Egress,PathletId,Bandwidth,Delay,Reliability,Status,Full_Path)
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
   