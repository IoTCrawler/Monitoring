import threading
import logging
from configuration import Config
from fault_recovery.fault_recovery_mcmc import FaultRecoveryMCMC
from fault_recovery.fault_recovery_bme import FaultRecoveryBME

RECOVERY_METHOD_VARIABLE_NAME = "RECOVERY_METHOD"

logger = logging.getLogger('monitoring')

class FaultRecovery:

    def __init__(self):
        self.predictors = {}
        self.recoveryMethods = {"BME" : FaultRecoveryBME, "MCMC" : FaultRecoveryMCMC}

    def reset(self):
        self.predictors = {}

    def newSensor(self, sensorID, entity):
        logger.debug("FR newSensor called")
        if sensorID in self.predictors:
            # the sensor was previously faulty and we already have a instance of the FR
            return

        # TODO: Automated way to destinguish which FaultRecovery method to use?
        m = Config.getEnvironmentVariable(RECOVERY_METHOD_VARIABLE_NAME)
        if not m in self.recoveryMethods:
            logger.debug("recovery method " + m + " not supported")
            return
        # fr = FaultRecoveryMCMC()
        fr = self.recoveryMethods[m]()
        self.predictors[sensorID] = fr

        t = threading.Thread(target=fr.newSensor, args=(sensorID, entity,))
        t.start()


    def update(self, sensorID, value):
        logger.debug("FR update callled")
        if sensorID in self.predictors:
            return self.predictors[sensorID].update(sensorID, value)
        else:
            # training not complete yet?
            # TODO: check if there is a pickle file from an earlier run. In that case we can create a FR instance without training
            return None
