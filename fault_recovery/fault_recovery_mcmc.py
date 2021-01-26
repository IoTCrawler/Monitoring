import threading

from ngsi_ld import ngsi_parser
from other import utils
import numpy as np
from copy import deepcopy
import dateutil.parser as dparser
import pymc3 as pm
import pickle
import os.path


class FaultRecoveryMCMC:
    # ................................................ Variables ......................................................
    stepFunction = 0  # 0 = metropolis, 1 = hmc, 2 = nuts
    sigmaMCMC = 0.1
    generatedNumber = 500
    windows = 8
    burninTime = 200

    # ................................................ Functions() ....................................................

    def makeModelFilename(self, filename):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", filename.replace(':', '_'))

    def minutesSinceMidnight(self, timestamp):
        return timestamp.hour * 60 + timestamp.minute
        # return timestamp.day * 1440 + timestamp.hour * 60 + timestamp.minute

    def newSensor(self, sensorID, entity):
        # print("FR newSensor called")
        muValue, sigmaValue, genNumber = self.get_norm_dist(sensorID)
        if not muValue:
            # no training data
            return
        synthetic_data_model = pm.Model()
        with synthetic_data_model:
            observationProb = pm.Normal('observation_value', mu=muValue, sigma=sigmaValue)
            returns = pm.Normal('out', mu=observationProb, sigma=self.sigmaMCMC)  # df
            if self.stepFunction == 0:
                step = pm.Metropolis()
            elif self.stepFunction == 1:
                step = pm.HamiltonianMC()
            else:
                step = pm.NUTS()

            # trace = pm.sample(self.generatedNumber, step=step, init='advi+adapt_diag', cores=1, chains=1)
            trace = pm.sample(genNumber, step=step, init='advi+adapt_diag', cores=1, chains=1)
        fname = pm.save_trace(trace, 'LearningOutput' + str(sensorID) + '.trace', overwrite=True)
        traceArray = trace['out']
        final = []
        # print("lta:", len(traceArray))
        # for i in range(self.burninTime):
        for i in range(genNumber):
            final.append(traceArray[i])
        finalArray = np.asarray(final)
        # print("N:", len(finalArray))
        pickle_out = open(self.makeModelFilename("modelout_" + sensorID + ".pickle"), "wb")
        pickle.dump(finalArray, pickle_out)
        pickle_out.close()
        return

    def update(self, sensorID, ts):
        # print("FR update callled")
        # timeStamp = dparser.parse(str(ts), fuzzy=True).timestamp() % 10000
        timeStamp = np.float64(self.minutesSinceMidnight(dparser.parse(str(ts), fuzzy=True)))
        # print("current ts:", timeStamp)
        missingValuePosition = 4
        # pickle_in_data = open("models/modelout.pickle", "rb")
        pickle_in_data = open(self.makeModelFilename("modelout_" + sensorID + ".pickle"), "rb")
        pickle_in_time = open(self.makeModelFilename("timestamps_" + sensorID + ".pickle"), "rb")
        # myinputTime = pickle.load(pickle_in_time) % 10000  # extract the time
        myinputTime = pickle.load(pickle_in_time)
        # print("U1:", len(myinputTime), myinputTime)
        myinput = pickle.load(pickle_in_data)
        for i in range(len(myinputTime)):
            if (myinputTime[i] == timeStamp):
                missingValuePosition = i
                # print("U3: found timestamp")
                break
        # print("U2:", missingValuePosition, myinput[abs(missingValuePosition - self.windows): abs(missingValuePosition + self.windows)], abs(missingValuePosition - self.windows), abs(missingValuePosition + self.windows), len(myinput))
        # TODO: test if myinput is long enough
        imputedValue = int(
            np.mean(myinput[abs(missingValuePosition - self.windows): abs(missingValuePosition + self.windows)]))
        pickle_in_time.close()
        pickle_in_data.close()
        # print("predicted value:", imputedValue)
        return imputedValue

    def get_norm_dist(self, sensorID):

        dataSamples = utils.loadTrainingData(sensorID)
        if not sensorID in dataSamples:
            return None, None
        dataSampleItems = dataSamples[sensorID]
        originalValues = np.zeros((len(dataSampleItems), 2))
        i = 0
        for item in dataSampleItems:
            elementTime = item["timestamp"]
            timeParse = dparser.parse(str(elementTime), fuzzy=True)
            # originalValues[i][1] = timeParse.strftime("%Y%m%d%H%M")
            originalValues[i][1] = self.minutesSinceMidnight(timeParse)
            originalValues[i][0] = item["value"]
            i += 1

        ind = np.argsort(originalValues[:, 1])
        originalValuesSorted = originalValues[ind]
        # print(originalValuesSorted)
        # print("T1:", originalValuesSorted[:, 1], len(originalValuesSorted[:, 1]))
        uniqueValues = np.unique(originalValuesSorted[:, 1])
        # print("T2:", uniqueValues, len(uniqueValues))
        timestamp_filename = self.makeModelFilename("timestamps_" + sensorID + ".pickle")
        # pickle_out = open("timestamps.pickle", "wb")
        pickle_out = open(timestamp_filename, "wb")
        # pickle.dump(originalValuesSorted[:, 1], pickle_out)
        pickle.dump(uniqueValues, pickle_out)
        pickle_out.close()

        originalValuesSortedFixedTimeindexes = deepcopy(originalValuesSorted)
        for i in range(len(originalValuesSorted)):
            originalValuesSortedFixedTimeindexes[i][1] = i

        muValue = np.mean(originalValuesSortedFixedTimeindexes[:, 0])
        sigmaValue = np.abs(np.max(originalValuesSortedFixedTimeindexes[:, 0])
                            - np.min(originalValuesSortedFixedTimeindexes[:, 0]))

        return muValue, sigmaValue, len(uniqueValues)
