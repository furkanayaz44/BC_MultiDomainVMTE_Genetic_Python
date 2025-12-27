import random
from blockchain.Transaction import Transaction

def generate_population(vn_count, candidateDomains, population_size):
    """
    Rastgele başlangıç popülasyonu oluşturur.

    :param vn_count: Kromozom başına alel sayısı (gene sayısı)
    :param candidateDomains: Her gen için seçilebilecek değerlerin listesi (2D array)
    :param population_size: Popülasyonun toplam kromozom sayısı
    :return: Başlangıç popülasyonu (liste)
    """
    population = []
    for _ in range(population_size):
        chromosome = [random.choice(candidateDomains[i]) for i in range(vn_count)]
        population.append(chromosome)
    return population

def fitness_function(chromosome):

    #allTransaction = Transaction()
    allTransaction,edgeRouter = read_transactions(f"topologies/NSFNET/transactions/transaction_substrate_14_21_1_nodeperisp_5.txt")

    """
    Fitness fonksiyonu: Her genetik algoritma için özelleştirilmelidir.

    :param chromosome: Değerlendirilecek kromozom
    :return: Fitness skoru (örnek: toplam değer)
    """
    return sum(chromosome)

def read_transactions(file_path):
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
                    Bandwidth = float(parts[5])
                    Delay = float(parts[6])
                    Reliability = parts[7]
                    Status= parts[8]
                    Full_Path = parts[9]
                    # reliability = #5th matrix index 

                    all_transaction = Transaction(TransactionId,ASId,Ingress,Egress,PathletId,Bandwidth,Delay,Reliability,Status,Full_Path
)   
                    #print(all_transaction.getNumOfHops())
                    if (all_transaction.getASId()) == -1:
                        edgeRouter.append(all_transaction)
                    else:
                        all_transactions.append(all_transaction)
        return all_transactions,edgeRouter

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


def crossover(parent1, parent2, candidateDomains):
    """
    Çaprazlama işlemini gerçekleştirir.

    :param parent1: Birinci ebeveyn kromozomu
    :param parent2: İkinci ebeveyn kromozomu
    :param candidateDomains: Her gen için olası değerlerin listesi (2D array)
    :return: Çocuk kromozomu
    """
    child = []
    for i in range(len(parent1)):
        if parent1[i] != parent2[i]:
            # Eğer parent1 ve parent2 farklıysa %50-%50 olasılıkla seç
            child.append(random.choice([parent1[i], parent2[i]]))
        else:
            # Eğer parent1 ve parent2 aynıysa %80 olasılıkla diğer adayı seç
            remaining_values = [val for val in candidateDomains[i] if val != parent1[i]]
            if remaining_values and random.random() < 0.8:
                child.append(random.choice(remaining_values))
            else:
                child.append(parent1[i])
    return child

def genetic_algorithm(vn_count, candidateDomains, population_size, iterations):
    """
    Genetik algoritma işlemini gerçekleştirir.

    :param vn_count: Kromozom başına alel sayısı (gene sayısı)
    :param candidateDomains: Her gen için seçilebilecek değerlerin listesi (2D array)
    :param population_size: Başlangıç popülasyonu büyüklüğü
    :param iterations: Maksimum iterasyon sayısı
    :return: En iyi kromozom ve fitness değeri
    """
    # Başlangıç popülasyonunu oluştur
    population = generate_population(vn_count, candidateDomains, population_size)

    for iteration in range(iterations):
        # Fitness değerlerini hesapla
        fitness_scores = [(chromosome, fitness_function(chromosome)) for chromosome in population]

        #!!!! eksi kod fitnes için
        # En iyi kromozomu bul
        best_chromosome, best_fitness = max(fitness_scores, key=lambda x: x[1])

        #yeni kod %10 sonraki nesile geçmesi için yazıldı
         # En iyi kromozomu bul
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        best_chromosome, best_fitness = fitness_scores[0]

        # Yeni popülasyonu oluştur
        new_population = [chromosome for chromosome, _ in fitness_scores[:max(1, population_size // 20)]]
        #print(new_population)
        
        # Yeni popülasyonu oluştur
    
        #print(population)
        while len(new_population) < population_size:
            # Rastgele seçim
            parent1, parent2 = random.sample(population, 2)

            # Çaprazlama (crossover)
            child1 = crossover(parent1, parent2, candidateDomains)
            #child2 = crossover(parent1, parent2, candidateDomains)
            # Mutasyon (mutation)
            if random.random() < 0.1:  # %10 mutasyon olasılığı
                mutation_index = random.randint(0, vn_count - 1)
                child1[mutation_index] = random.choice(candidateDomains[mutation_index])
            # if random.random() < 0.1:  # %10 mutasyon olasılığı
            #     mutation_index = random.randint(0, vn_count - 1)
            #     child2[mutation_index] = random.choice(candidateDomains[mutation_index])
            new_population.append(child1)
            #new_population.append(child2)

        population = new_population
        #print("--------------------------")
        #print(population)
        #print(f"Iteration {iteration + 1}: Best Fitness = {best_fitness}")

    return best_chromosome, best_fitness