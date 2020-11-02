import threading
from fault_recovery_mcmc import FaultRecoveryMCMC

class FaultRecovery:
    # ................................................ Variables ......................................................

    # ................................................ Functions() ....................................................

    def __init__(self):
        self.predictors = {}

    def newSensor(self, sensorID, entity):
        print("FR newSensor called")
        if sensorID in self.predictors:
            # the sensor was previously faulty and we already have a instance
            return

        # TODO: How to destinguish which FaultRecovery method to use?
        fr = FaultRecoveryMCMC()
        self.predictors[sensorID] = fr

        t = threading.Thread(target=fr.newSensor, args=(sensorID, entity,))
        t.start()


    def update(self, sensorID, value):
        print("FR update callled")
        if sensorID in self.predictors:
            return self.predictors[sensorID].update(sensorID, value)
        else:
            # training not complete yet?
            # TODO: check if there is a pickle file from an earlier run. In that case we can create a FR instance without training
            return None
