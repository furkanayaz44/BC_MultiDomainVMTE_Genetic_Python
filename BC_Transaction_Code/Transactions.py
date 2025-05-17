class Transactions:
    def __init__(self, PreviousAS, CurrentAS, NextAS, Bandwidth, Delay, Hop, Full_Path):
        self.PreviousAS = PreviousAS
        self.CurrentAS = CurrentAS
        self.NextAS = NextAS
        self.Bandwidth = Bandwidth
        self.Delay = Delay
        self.Hop = Hop
        self.Full_Path = Full_Path

    def __repr__(self):
        return f"Transactions(PreviousAS={self.PreviousAS}, CurrentAS={self.CurrentAS}, NextAS={self.NextAS}, Bandwidth={self.Bandwidth}, Delay={self.Delay}, Hop={self.Hop}, Full_Path='{self.Full_Path}')"

    def get_full_path(self):
        return self.Full_Path

    def get_PreviousAS(self):
        return self.PreviousAS
    
    def get_CurrentAS(self):
        return self.CurrentAS
    
    def get_NextAS(self):
        return self.NextAS
    
    def get_Bandwidth(self):
        return self.Bandwidth
    
    def get_numofHops(self):
        return self.Hop