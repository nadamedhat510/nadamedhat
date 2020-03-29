# -*- coding: utf-8 -*-
"""
Created on Sun Mar 15 17:09:40 2020

@author: Gehan Mohamed
"""
import pyedflib
import numpy as np
from scipy import signal
from scipy.signal import butter, lfilter
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import time
from scipy import interpolate as interp
#import interpolate as interp
from pywt import wavedec
import pywt

# DATASET: https://physionet.org/pn6/chbmit/
sampleRate = 256
pathDataSet = ''# path of the dataset
FirstPartPathOutput='' #path where the spectogram will be saved
#patients = ["01", "02", "03", "05", "09", "10", "13", "14", "18", "19", "20", "21", "23"]
#nSeizure = [7, 3, 6, 5, 4, 6, 5, 5, 6, 3, 5, 4, 5]
#patients = ["01", "02", "05", "19", "21", "23"]
patients=["01"]
_30_MINUTES_OF_DATA = 256*60*30
_MINUTES_OF_DATA_BETWEEN_PRE_AND_SEIZURE = 3#In teoria 5 come l'SPH ma impostato a 3 per considerare alcune seizure prese nel paper
_MINUTES_OF_PREICTAL = 30
_SIZE_WINDOW_IN_SECONDS = 30
_SIZE_WINDOW_SPECTOGRAM = _SIZE_WINDOW_IN_SECONDS*256
nSpectogram=0
signalsBlock=None
SecondPartPathOutput=''
legendOfOutput=''
isPreictal=''
def loadParametersFromFile(filePath):
    global pathDataSet
    global FirstPartPathOutput
    if(os.path.isfile(filePath)):
        with open(filePath, "r") as f:
                line=f.readline()
                if(line.split(":")[0]=="pathDataSet"):
                    pathDataSet=line.split("@")[1].strip()
                line=f.readline()
                if(line.split(":")[0]=="FirstPartPathOutput"):
                 FirstPartPathOutput=line.split("@")[1].strip()
                    
                    # Filtro taglia banda
def butter_bandstop_filter(data, lowcut, highcut, fs, order):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq

    i, u = butter(order, [low, high], btype='bandstop')
    y = lfilter(i, u, data)
    return y

# Filtro taglia banda, passa alta
def butter_highpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    y = lfilter(b, a, data) 
    return y
   

#Creazione del puntatore al file del paziente con indice uguale a index
def loadSummaryPatient(index):
    f = open(pathDataSet+'chb'+patients[index]+'/chb'+patients[index]+'-summary.txt', 'r')
    return f

# Caricamento dei dati di un paziente(indexPatient). I dati sono presi dal file con il nome indicato in fileOfData
# Restituisce un vettore numpy con i dati del paziente contenuti nel file
def loadDataOfPatient(indexPatient, fileOfData):
    f = pyedflib.EdfReader(pathDataSet+'chb'+patients[indexPatient]+'/'+fileOfData)  # https://pyedflib.readthedocs.io/en/latest/#description
    n = f.signals_in_file
    sigbufs = np.zeros((n, f.getNSamples()[0]))
    for i in np.arange(n):
        sigbufs[i, :] = f.readSignal(i)
    sigbufs=cleanData(sigbufs, indexPatient)
    return sigbufs


def cleanData(Data, indexPatient):
    if(patients[indexPatient] in ["19","21"]):
        Data=np.delete(Data, 22, axis=0)
        Data=np.delete(Data, 17, axis=0)
        Data=np.delete(Data, 12, axis=0)
        Data=np.delete(Data, 9, axis=0)
        Data=np.delete(Data, 4, axis=0)
    return Data

# Conversione di una stringa indicante un tempo in un oggetto di tipo datetime
# e pulizia di date che non rispettano i limiti delle ore
def getTime(dateInString):
    time=0
    try:
        time = datetime.strptime(dateInString, '%H:%M:%S')
    except ValueError:
        dateInString=" "+dateInString
        if(' 24' in dateInString):
            dateInString = dateInString.replace(' 24', '23')
            time = datetime.strptime(dateInString, '%H:%M:%S')
            time += timedelta(hours=1)
        else:
            dateInString = dateInString.replace(' 25', '23')
            time = datetime.strptime(dateInString, '%H:%M:%S')
            time += timedelta(hours=2)
    return time

def saveSignalsOnDisk(signalsBlock, nSpectogram):
    global SecondPartPathOutput
    global FirstPartPathOutput
    global legendOfOutput
    global isPreictal

    if not os.path.exists(FirstPartPathOutput):
        os.makedirs(FirstPartPathOutput)
    if not os.path.exists(FirstPartPathOutput+SecondPartPathOutput):
        os.makedirs(FirstPartPathOutput+SecondPartPathOutput) 
    print('HERE\n')
    print(FirstPartPathOutput+SecondPartPathOutput+'/spec_'+isPreictal+'_'+str(nSpectogram-signalsBlock.shape[0])+'_'+str(nSpectogram-1))
    print('HERE\n')
    np.save(FirstPartPathOutput+SecondPartPathOutput+'/spec_'+isPreictal+'_'+str(nSpectogram-signalsBlock.shape[0])+'_'+str(nSpectogram-1), signalsBlock)
    legendOfOutput=legendOfOutput+str(nSpectogram-signalsBlock.shape[0])+' '+str(nSpectogram-1) +' '+SecondPartPathOutput+'/spec_'+isPreictal+'_'+str(nSpectogram-signalsBlock.shape[0])+'_'+str(nSpectogram-1) +'.npy\n'
 
    
def createSpectrogram(data, S=0):
    global nSpectogram
    global signalsBlock
    global inB
    signals=np.zeros((22,59,114))
    #t=data.shape
    #print(t)
    t=0
    movement=int(S*256)
    if(S==0):
        movement=_SIZE_WINDOW_SPECTOGRAM        
    while data.shape[1]-(t*movement+_SIZE_WINDOW_SPECTOGRAM) > 0:
        # CREAZIONE DELLO SPETROGRAMMA PER TUTTI I CANALI
        for i in range(0, 22):
            start = t*movement
            stop = start+_SIZE_WINDOW_SPECTOGRAM
            signals[i,:]=wavelet(data[i,start:stop])
            #z=data[i,start:stop].shape
            #print(z)
           # spe=createSpecAndPlot(data[i,start:stop])
        if(signalsBlock is None):
            signalsBlock=np.array([signals])
        else:
            signalsBlock=np.append(signalsBlock, [signals], axis=0)
        nSpectogram=nSpectogram+1
        if(signalsBlock.shape[0]==50):
            saveSignalsOnDisk(signalsBlock, nSpectogram)
            signalsBlock=None
            # SALVATAGGIO DI SIGNALS  
        t = t+1
    
    
        
    return (data.shape[1]-t*_SIZE_WINDOW_SPECTOGRAM)*-1    
    
    # Divide i dati contenuti in data in finestre e crea gli spettrogrammi che vengono salvati sul disco
# S è il fattore che indica di quanto ogni finestra si sposta
# Restituisce i dati non considerati, ciò accade quando i dati non sono divisibili per la lunghezza della finestra


    #fig, ax = plt.subplots(figsize=(6,1))
    #ax.set_title("interictal data: ")
    #ax.plot(data)
    #plt.show() #fig, axarr = plt.subplots(nrows=5, ncols=2, figsize=(6,6))
    #for ii in range(5):
        #coeff_d=d1,d2,d3,d4,d5
        #(data, coeff_d) = pywt.dwt(data, waveletname)
def wavelet(data):
    waveletname = 'sym5'
    coeffs = wavedec(data, 'sym5', level=5)
        #cA5,Cd5,cD4,cD5,cD3, cD2, cD1 = coeffs
    cA5,cD5,cD4,cD3,cD2,cD1=coeffs
    A_concate=[cD1,cD2,cD3,cD4,cD5]
    l=A_concate.shape
    print(l)
    
    
    
    #m=cD5.ndim
    #print(m)
    #coeffsarray = np.array(coeffs)
    
    #k=coeffsarray.shape
    #print(k)
    #print(coeffsarray)
    #A=numpy.array([[0,1,2,3], [2,3,4]], dtype=object)
    #A=[[cD1],[cD2],[cD3],[cD4],[cD5]]
    # Plot histogram of versicolor petal lengths
    #plt.hist(A)
    # Show histogram
    ##plt.show()
    #m=A.shape
   
    
    #print(A)
    #n=cD5.shape
    #print(n)
    #plt.bar(np.arange(len(cD5)),cD5)
    
    
        #v=coeff_d.shape
        #print(v)
        

      #  axarr[ii, 0].plot(data, 'r')
       # axarr[ii, 1].plot(coeff_d, 'g')
        #axarr[ii, 0].set_ylabel("Level {}".format(ii + 1), fontsize=14, rotation=90)
        #axarr[ii, 0].set_yticklabels([])
        #if ii == 0:
         #   axarr[ii, 0].set_title("Approximation coefficients", fontsize=14)
          #  axarr[ii, 1].set_title("Detail coefficients", fontsize=14)
        #axarr[ii, 1].set_yticklabels([])
    #plt.tight_layout()
    #plt.show()
    
    #coeffs = pywt.wavedec(data, wavelet='sym5', level=5)
    #p=coeffs.shape
    #print(p)
    #arr, coeff_slices = pywt.coeffs_to_array(coeff_d)
    #z=coeff_slices.shape
    #print(z)
    
   # return coeff_slices
       
       

        #print(d)
     #   axarr[ii, 0].plot(data, 'r')
      #  axarr[ii, 1].plot(coeff_d, 'g')
       # axarr[ii, 0].set_ylabel("Level {}".format(ii + 1), fontsize=14, rotation=90)
        #axarr[ii, 0].set_yticklabels([])
        #if ii == 0:
        #    axarr[ii, 0].set_title("Approximation coefficients", fontsize=14)
         #   axarr[ii, 1].set_title("Detail coefficients", fontsize=14)
          #  axarr[ii, 1].set_yticklabels([])
           # plt.tight_layout()
           # plt.show()



    
    
#Classe usata per rappresentare intervalli di dati, sia Preictal che Interictal
class PreIntData:
    start=0
    end=0
    def __init__(self, s, e):
        self.start=s
        self.end=e
        
        #Classe usata per tenere i dati dei file, data e ora inizio e fine e nome del file associato
class FileData:
    start=0
    end=0
    nameFile=""
    def __init__(self, s, e, nF):
        self.start=s
        self.end=e
        self.nameFile=nF


def createArrayIntervalData(fSummary):
    interictalInterval=[]
    preictalInteval=[]
    interictalInterval.append(PreIntData(datetime.min, datetime.max))
    files=[]
    firstTime=True
    oldTime=datetime.min # equivalente di 0 nelle date
    startTime=0
    line=fSummary.readline()
    endS=datetime.min
    while(line):
        data=line.split(':')
        if(data[0]=="File Name"):
            nF=data[1].strip()
            s=getTime((fSummary.readline().split(": "))[1].strip())
            if(firstTime):
                interictalInterval[0].start=s
                firstTime=False
                startTime=s
            while s<oldTime:#se cambia di giorno aggiungo 24 ore alla data
                s=s+ timedelta(hours=24)
            oldTime=s
            endTimeFile=getTime((fSummary.readline().split(": "))[1].strip())
            while endTimeFile<oldTime:#se cambia di giorno aggiungo 24 ore alla data
                endTimeFile=endTimeFile+ timedelta(hours=24)
            oldTime=endTimeFile
            files.append(FileData(s, endTimeFile,nF))
            for j in range(0, int((fSummary.readline()).split(':')[1])):
                secSt=int(fSummary.readline().split(': ')[1].split(' ')[0])
                secEn=int(fSummary.readline().split(': ')[1].split(' ')[0])
                ss=s+timedelta(seconds=secSt)- timedelta(minutes=_MINUTES_OF_DATA_BETWEEN_PRE_AND_SEIZURE+_MINUTES_OF_PREICTAL)
                if((len(preictalInteval)==0 or ss > endS) and ss-startTime>timedelta(minutes=20)):
                    ee=ss+ timedelta(minutes=_MINUTES_OF_PREICTAL) 
                    preictalInteval.append(PreIntData(ss,ee))
                endS=s+timedelta(seconds=secEn)
                ss=s+timedelta(seconds=secSt)- timedelta(hours=4) 
                ee=s+timedelta(seconds=secEn)+ timedelta(hours=4) 
                if(interictalInterval[len(interictalInterval)-1].start<ss and interictalInterval[len(interictalInterval)-1].end>ee):
                    interictalInterval[len(interictalInterval)-1].end=ss
                    interictalInterval.append(PreIntData(ee, datetime.max))
                else:
                    if(interictalInterval[len(interictalInterval)-1].start<ee):
                        interictalInterval[len(interictalInterval)-1].start=ee
        line=fSummary.readline()
    fSummary.close()
    interictalInterval[len(interictalInterval)-1].end=endTimeFile
    return preictalInteval, interictalInterval, files





def main():
    global SecondPartPathOutput
    global FirstPartPathOutput
    global legendOfOutput
    global nSpectogram
    global signalsBlock
    global isPreictal
    print("START \n")
    loadParametersFromFile("PARAMETERS_DATA_EDITING.txt")
    print("Parameters loaded")
    for indexPatient in range(0, len(patients)):
        print("Working on patient "+patients[indexPatient])
        legendOfOutput=""
        allLegend=""
        nSpectogram=0
        
        SecondPartPathOutput='/paz'+ patients[indexPatient]
        f = loadSummaryPatient(indexPatient)
        preictalInfo, interictalInfo, filesInfo=createArrayIntervalData(f)
        if(patients[indexPatient]=="19"):
            preictalInfo.pop(0) #Eliminazione dei dati della prima seizure perchè non viene considerata
        print("Summary patient loaded")
        
         #INIZIO ciclo gestione interictal data
        print("START creation interictal spectrogram")
        totInst=0
        #c=0
        #d=0   
        interictalData = np.array([]).reshape(22,0)       
        indexInterictalSegment=0      
        isPreictal=''
        for fInfo in filesInfo:
            fileS=fInfo.start
            fileE=fInfo.end
            intSegStart=interictalInfo[indexInterictalSegment].start
            intSegEnd=interictalInfo[indexInterictalSegment].end
            while(fileS>intSegEnd and indexInterictalSegment<len(interictalInfo)):
                indexInterictalSegment=indexInterictalSegment+1
                intSegStart=interictalInfo[indexInterictalSegment].start
                intSegEnd=interictalInfo[indexInterictalSegment].end
            start=0
            end=0
            if(not fileE<intSegStart or fileS>intSegEnd):
                if(fileS>=intSegStart):
                    start=0
                else:
                    start=(intSegStart-fileS).seconds
                if(fileE<=intSegEnd):
                    end=None
                else:
                    end=(intSegEnd-fileS).seconds
                tmpData=loadDataOfPatient(indexPatient, fInfo.nameFile)
                if(not end==None):
                    end=end*256
                if(tmpData.shape[0]<22):
                    print(patients[indexPatient] +"  HA UN NUMERO MINORE DI CANALI")
                else:
                    interictalData=np.concatenate((interictalData, tmpData[0:22,start*256:end]), axis=1)
                    notUsed= createSpectrogram(interictalData)
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
if __name__ == '__main__':
    main()                    
                    