import pandas as pd
import numpy as np
import itertools

    
class Detector:
    
    def __init__(self):
        self.df, self.df_pb = {}, {}
        self.states = ['up', 'down', 'stable']
        self.difference_uniq = []
        self.counts = {}
        self.fault_flag, self.flag = 0, 0
        self.q, self.max_seq = 1, 0
        self.W = 15                 #can be changed to input parameters
        self.fault_threshold = 0.2  #can be changed to input parameters
        self.alphas = np.ones(self.W-1)
        self.record = []
        
        
    def get_data(self, data):
        # self.df = pd.read_csv(file_path)
        self.df = pd.DataFrame(data)
    
    def max_repetitions(self, difference):
        rep_diff = [[x[0], len(list(x[1]))] for x in itertools.groupby(difference)]
        list_counts = []
        for i in self.difference_uniq:
            container = []
            for j in rep_diff:
                if i == j[0]:
                    container.append(j[1])
            list_counts.append(container)
            self.counts[i] = max(container)
    
    def train(self):
        X_train = self.df.value.iloc[0:1000]
        difference = [round(j-i,1) for i, j in zip(X_train[:-1], X_train[1:])]
        self.difference_uniq = list(set(difference))
        self.difference_uniq = sorted(self.difference_uniq)
        self.record = np.zeros((len(self.difference_uniq),len(self.states)))
        #Count maximum repetitions to detect stuck-at faults
        self.max_repetitions(difference)    
        #Define states for transitions
        table = np.zeros((len(self.difference_uniq),len(self.states)))
        
        for j in range(1,len(difference)-1):
            ind1 = self.difference_uniq.index(difference[j])
            if difference[j]<difference[j-1]:
                ind2 = 1
            elif difference[j]>difference[j-1]:
                ind2 = 0
            elif difference[j] == difference[j-1]:
                ind2 = 2
            table[ind1][ind2]+=1
        
        self.df_pb = pd.DataFrame.from_records(table, index=self.difference_uniq)
        #self.df_pb.loc[:,:] = round(self.df_pb.loc[:,:].div(self.df.sum(axis=1), axis=0),1)*10
        self.df_pb.loc[:,:] = round(self.df_pb.loc[:,:].div(self.df_pb.sum(axis=1), axis=0),1)*10
        
        
    def detector(self, test_difference):
        R = 0
        fault_ind = 0
        
        if len(test_difference)<2:
            if test_difference[0] in self.difference_uniq:
                alpha_current = 1
            else:
                alpha_current = 0
                self.flag = 1           
            R = (sum(self.alphas)/(self.W-1))-(sum(self.alphas)+alpha_current)/self.W
            self.q = self.q - 2*R
            self.alphas = np.delete(self.alphas,0)
            self.alphas = np.append(self.alphas,alpha_current)
            if self.q<self.fault_threshold:
                fault_ind = 'F'
            else:
                fault_ind = 'N'
        else:
            i = 1
            if test_difference[i] in self.difference_uniq:
                if test_difference[i] == test_difference[i-1]:
                    self.max_seq +=1
                else:
                    self.max_seq = 0
                if self.max_seq > self.counts[test_difference[i]]:
                    alpha_current = 0
                elif self.flag == 1: ###NoteToSelf-- this can be changed to calculating the difference and comparing with current states
                    self.flag = 0
                    alpha_current = 1
                else:
                    x = self.difference_uniq.index(test_difference[i])
                    if test_difference[i]<test_difference[i-1]:
                        y = 1
                    elif test_difference[i]>test_difference[i-1]:
                        y = 0
                    elif test_difference[i] == test_difference[i-1]:
                        y = 2
                    self.record[x][y] +=1
                    if self.record[x][y] <= self.df_pb.loc[test_difference[i]][y]:
                        alpha_current = 1
                    else:
                        alpha_current = 0
                    if sum(self.record[x]) == sum(self.df_pb.loc[test_difference[i]]):
                        self.record[x] = 0
                
            else: #fault - state not seen before
                self.flag = 1
                alpha_current = 0
                if test_difference[i]>max(self.difference_uniq)*1.5 or test_difference[i]<min(self.difference_uniq)*1.5:
                    fault_ind = 'F'
                    self.fault_flag = 1
            self.alphas = np.delete(self.alphas,0)
            self.alphas = np.append(self.alphas,alpha_current)
            R = (sum(self.alphas)/(self.W-1))-(sum(self.alphas)+alpha_current)/self.W
            self.q = self.q - 2*R
            if self.q<0:
                self.q=0
            
            if self.fault_flag == 0:
                if self.q<self.fault_threshold:
                    fault_ind = 'F'
                else:
                    fault_ind = 'N'
            else:
                self.fault_flag = 0
        return fault_ind
        
if __name__ == '__main__':
    path = 'Pa1_1.csv'
    x = Detector()
    x.get_data(path)
    x.train()
    
    test_difference = [1,2]
    for i in range(0,40):
        print(x.detector(test_difference))
        del test_difference[0]
        test_difference.append(i)
