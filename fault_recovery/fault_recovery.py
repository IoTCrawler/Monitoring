import threading

from ngsi_ld import ngsi_parser
from other import utils
import numpy as np
from copy import deepcopy
import dateutil.parser as dparser
import pymc3 as pm
import pickle


class FaultRecovery:
    # ................................................ Variables ......................................................
    stepFunction = 0  # 0 = metropolis, 1 = hmc, 2 = nuts
    sigmaMCMC = 0.1
    generatedNumber = 500
    windows = 8
    burninTime = 200

    # ................................................ Functions() ....................................................

    def newSensor(self, sensorID, entity):
        print("FR newSensor called")

        t = threading.Thread(target=self._newSensor, args=(entity,))
        t.start()

    def _newSensor(self, sensorID, entity):
        print("FR newSensor called")
        muValue, sigmaValue = self.get_norm_dist(sensorID)
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

            trace = pm.sample(self.generatedNumber, step=step, init='advi+adapt_diag', cores=1, chains=1)
        fname = pm.save_trace(trace, 'LearningOutput' + str(sensorID) + '.trace', overwrite=True)
        traceArray = trace['out']
        final = []
        for i in range(self.burninTime):
            final.append(traceArray[i])
        finalArray = np.asarray(final)

        pickle_out = open("modelout_" + str(sensorID) + ".pickle", "wb")
        pickle.dump(finalArray, pickle_out)
        pickle_out.close()
        return

    def update(self, sensorID, value):
        print("FR update callled")
        timeStamp = value
        missingValuePosition = 4
        # pickle_in_data = open("models/modelout.pickle", "rb")
        pickle_in_data = open("models/modelout_" + str(sensorID) + ".pickle", "rb")
        pickle_in_time = open("models/timestamps_" + str(sensorID) + ".pickle", "rb")
        myinputTime = pickle.load(pickle_in_time) % 10000  # extract the time
        for i in range(len(myinputTime)):
            if (myinputTime[i] == timeStamp):
                missingValuePosition = i
        myinput = pickle.load(pickle_in_data)
        imputedValue = int(
            np.mean(myinput[abs(missingValuePosition - self.windows): abs(missingValuePosition + self.windows)]))
        pickle_in_time.close()
        pickle_in_data.close()
        return imputedValue

    def get_norm_dist(self, sensorID):

        dataSamples = utils.loadTrainingData(sensorID)
        dataSampleItems = dataSamples[sensorID]
        originalValues = np.zeros((len(dataSampleItems), 2))
        i = 0
        for item in dataSampleItems:
            elementTime = item["timestamp"]
            timeParse = dparser.parse(str(elementTime), fuzzy=True)
            originalValues[i][1] = timeParse.strftime("%Y%m%d%H%M")
            originalValues[i][0] = item["value"]
            i += 1

        ind = np.argsort(originalValues[:, 1])
        originalValuesSorted = originalValues[ind]

        timestamp_filename = "models/timestamps_" + str(sensorID) + ".pickle"
        # pickle_out = open("timestamps.pickle", "wb")
        pickle_out = open(timestamp_filename, "wb")
        pickle.dump(originalValuesSorted[:, 1], pickle_out)
        pickle_out.close()

        originalValuesSortedFixedTimeindexes = deepcopy(originalValuesSorted)
        for i in range(len(originalValuesSorted)):
            originalValuesSortedFixedTimeindexes[i][1] = i

        muValue = np.mean(originalValuesSortedFixedTimeindexes[:, 0])
        sigmaValue = np.abs(np.max(originalValuesSortedFixedTimeindexes[:, 0])
                            - np.min(originalValuesSortedFixedTimeindexes[:, 0]))

        return muValue, sigmaValue

# def _newSensor(self, sensorID, entity):
# 	print("FR newSensor called")
#
# 	ngsi_id, ngsi_type = ngsi_parser.get_IDandType(entity)
# 	result = utils.loadTrainingData(ngsi_id)
# 	print(result)

# def update(self, sensorID, value):
# 	print("FR update callled")
