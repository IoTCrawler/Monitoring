# import os
import threading
import requests
import logging

from ngsi_ld import ngsi_parser
from ngsi_ld.ngsi_parser import NGSI_Type
from fault_detection.detector import Detector
from other import utils

logger = logging.getLogger('monitoring')

class FaultDetection:

    def __init__(self):
#        self.newSensor(entity)
        self.detectors = {}
        self.old_values = {}
        self.no_of_faults = {}
        self.no_of_misses = {}
        self.missedValues = {}
        self.createdVS = {}
        self.reset_counter = {}
        self.prev_difference = {}
        #self.no_of_misses = {}
        #self.updateIntervals = {}



    def newSensor(self, entity):
        logger.debug("FD newSensor called")
        # ngsi_id, ngsi_type = ngsi_parser.get_IDandType(ngsi_data)
        # # check type
        # if ngsi_type is NGSI_Type.Sensor:# or NGSI_Type.NGSI_Type.Sensor:StreamObservation:
        # # newSensorID = self.ID()+ "_FD"
        #     ngsi_data['id'] = ngsi_data['id'] + "_FD" # Where to update qoi:Artificiality?
        #     self.create_ngsi_entity(ngsi_data)
        ##############################################################################
        t = threading.Thread(target=self._newSensor, args=(entity,))
        t.start()


    def _newSensor(self, entity):
        ngsi_id, ngsi_type = ngsi_parser.get_IDandType(entity)
        self.no_of_misses[ngsi_id] = 0
        self.no_of_faults[ngsi_id] = 0
        self.createdVS[ngsi_id] = 0
        self.missedValues[ngsi_id] = None
        self.old_values[ngsi_id] = None
        self.reset_counter[ngsi_id] = 0
        self.prev_difference[ngsi_id] = None
        #timeInterval, unit = ngsi_parser.get_sensor_updateinterval_and_unit(entity)
        #todo: if sensor has no training data, store values and create data

        result = utils.loadTrainingData(ngsi_id)

        if ngsi_id in result:
            logger.debug("FD - train for" + ngsi_id)
            self.detectors[ngsi_id] = Detector()
            self.detectors[ngsi_id].get_data(result[ngsi_id])
            self.detectors[ngsi_id].train()
            logger.debug("FD - training of " + ngsi_id + " finished")
        else:
            logger.debug("FD - no training data for " + ngsi_id + " found")

    #return 1 for create VS, 0 for dont
    def callVS(self, sensorID):
        if self.no_of_faults[sensorID] == 20 and self.createdVS[sensorID] == 0:
            self.createdVS[sensorID] = 1
            return 1
        else:
            return 0

    #return 2 to delete VS, 0 for dont
    def delVS(self, sensorID):
        if self.reset_counter[sensorID] > 10:
            self.no_of_faults[sensorID] = 0
            self.no_of_misses[sensorID] = 0
            if self.createdVS[sensorID] == 1:
                self.createdVS[sensorID] = 0
                return 2
        return 0

    #return: arg1 - 0,1 or 2 -> no operation, callVS, delete VS | arg2 - 0,1 -> Value found, Missing value
    def missingValue(self, sensorID, freq):
        if not sensorID in self.missedValues or self.missedValues[sensorID] == None:
            self.missedValues[sensorID] = freq
            return self.callVS(sensorID), 0 #no result from first value as no decrease in freq| todo: change this if freq always starts with 1
        freq_difference = freq - self.missedValues[sensorID]
        self.missedValues[sensorID] = freq
        if freq_difference <= 0 and freq != 1 :
            self.no_of_faults[sensorID] = self.no_of_faults[sensorID] + 1
            self.no_of_misses[sensorID] = self.no_of_misses[sensorID] + 1
            self.reset_counter[sensorID] = 0
            return self.callVS(sensorID), 1
        else:
            self.reset_counter[sensorID] = self.reset_counter[sensorID] + 1  #add a counter for better values before reset
            return self.delVS(sensorID), 0

    #return: arg1 - 0,1 or 2 -> no operation, callVS, delete VS | arg2 - 0,1 -> No fault, Fault
    def update(self, sensorID, value):
        if self.old_values[sensorID] == None:
            self.old_values[sensorID] = value
            return self.callVS(sensorID), 0 #skip if its the first value - No difference
        difference = [value - self.old_values[sensorID]]
        if self.prev_difference[sensorID] == None:
            self.prev_difference[sensorID] = difference[0]
        else:
            difference = [self.prev_difference[sensorID], difference[0]]
            self.prev_difference[sensorID] = difference[1]
        self.old_values[sensorID] = value
        #return 0 if normal return 1 if faulty
        if not sensorID in self.detectors:
            logger.debug("FD update called with sensor where no detector was trained for! (id=" + sensorID + ")")
            return self.delVS(sensorID), 0
        if self.detectors[sensorID].detector(difference) == 'F':
            self.no_of_faults[sensorID] = self.no_of_faults[sensorID] + 1
            self.reset_counter[sensorID] = 0
            return self.callVS(sensorID), 1
        else:
            #self.no_of_faults[sensorID] = 0
            self.reset_counter[sensorID] = self.reset_counter[sensorID] + 1
            return self.delVS(sensorID), 0
