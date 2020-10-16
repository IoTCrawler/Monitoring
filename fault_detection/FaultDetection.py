# import os
import threading
import requests


from ngsi_ld import ngsi_parser
from ngsi_ld.ngsi_parser import NGSI_Type
from fault_detection.detector import Detector
from other import utils

# REGISTRATION_CONTENT_TYPE = {'content-type': 'application/json'}
# REGISTRATION_FIWARE_SERVICE = {'fiware-service': 'openiot'}
# REGISTRATION_FIWARE_SERVICEPATH = {'fiware-servicepath': '/'}

# headers = {}
# headers.update({'content-type': 'application/ld+json'})
# headers.update({'accept': 'application/json'})

# SEND_LOCAL = True
# broker = os.environ['NGSI_ADDRESS']# = '155.54.95.2488:9090' #pass in class?

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

#     def patch_ngsi_entity(ngsi_msg, broker):
#     # for updating entity we have to delete id and type, first do copy if needed somewhere else
#         ngsi_msg_patch = dict(ngsi_msg)
#         ngsi_msg_patch.pop('id')
#         ngsi_msg_patch.pop('type')
#         url = "http://" + broker + "/ngsi-ld/v1/entities/" + ngsi_msg['id'] + "/attrs/"
#         r = requests.patch(url, json=ngsi_msg_patch, headers=headers)
#         print("Patch response:", r.text, "code", r.status_code)
#         if r.status_code == 204:
#             print("Successful patch " + ngsi_msg['id'])


#     def create_ngsi_entity(self,ngsi_msg):
#         t = threading.Thread(target=self._create_ngsi_entity, args=(ngsi_msg,))
#         t.start()

#     def _create_ngsi_entity(self, ngsi_msg):
# #        for broker in BROKERS:
#         print("save message to ngsi broker:", ngsi_msg)
#         try:
#             url = "http://" + broker + "/ngsi-ld/v1/entities/"
#             r = requests.post(url, json=ngsi_msg, headers=headers)
#             if r.status_code == 201:
#                 print("Successful creation of " + ngsi_msg['id'])
#             elif r.status_code == 400:
#                 print("Bad Request creating entity ", ngsi_msg['id'], r.text)
#             elif r.status_code == 409:
#                 print("Already Exists (", ngsi_msg['id'], "), patch it")
#                 self.patch_ngsi_entity(ngsi_msg, broker)
#             elif r.status_code == 500:
#                 print("Error while creating ngsi entity", r.text)
#                 print("Broker", broker, "Entity", ngsi_msg)
#             else:
#                 print("Answer:", r.text)
#         except requests.exceptions.ConnectionError:
#             print("server not reachable?")


    def newSensor(self, entity):
        print("FD newSensor called")
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
        result = utils.loadTrainingData(ngsi_id)
        self.no_of_misses[ngsi_id] = 0
        self.no_of_faults[ngsi_id] = 0
        self.createdVS[ngsi_id] = 0
        self.missedValues[ngsi_id] = None
        self.old_values[ngsi_id] = None
        self.reset_counter[ngsi_id] = 0
        self.prev_difference[ngsi_id] = None
        #timeInterval, unit = ngsi_parser.get_sensor_updateinterval_and_unit(entity)
        #todo: if sensor has no training data, store values and create data
        if ngsi_id in result:
            print("FD - train for", ngsi_id)
            self.detectors[ngsi_id] = Detector()
            self.detectors[ngsi_id].get_data(result[ngsi_id])
            self.detectors[ngsi_id].train()
            print("FD - training of", ngsi_id, "finished")
        else:
            print("no training data for", ngsi_id, "found")

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
        if self.missedValues[sensorID] == None:
            self.missedValues[sensorID] = freq
            return self.callVS(sensorID), 0 #no result from first value as no decrease in freq| todo: change this if freq always starts with 1
        freq_difference = freq - self.missedValues[sensorID]
        self.missedValue[sensorID] = freq
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
        if self.detectors[sensorID].detector(difference) == 'F':
            self.no_of_faults[sensorID] = self.no_of_faults[sensorID] + 1
            self.reset_counter[sensorID] = 0
            return self.callVS(sensorID), 1
        else:
            #self.no_of_faults[sensorID] = 0
            self.reset_counter[sensorID] = self.reset_counter[sensorID] + 1
            return self.delVS(sensorID), 0
