# import os
import threading
import requests


from ngsi_ld import ngsi_parser
from ngsi_ld.ngsi_parser import NGSI_Type
from fault_detection.detector import Detector
from others import utils

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
        self.missedValues = {}
        self.createdVS = {}
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
        #timeInterval, unit = ngsi_parser.get_sensor_updateinterval_and_unit(entity)
        #todo: if sensor has no training data, store values and create data
        if ngsi_id in result:
            self.detectors[ngsi_id] = Detector()
            self.detectors[ngsi_id].get_data(result[ngsi_id])
            self.detectors[ngsi_id].train()
        else:
            print("no training data for", ngsi_id, "found")
            
    def callVS(self, sensorID, call):
        if call == 'u':
            if self.no_of_faults[sensorID] == 20 and self.createdVS[sensorID] == 0:
                self.createdVS[sensorID] = 1
                return 'y'
            else:
                return 'n'
        if call == 'm':
            if self.no_of_misses[sensorID] == 20 and self.createdVS[sensorID] == 0:
                self.createdVS[sensorID] = 1
                return 'y'
            else:
                return 'n'
    
    #check if we need to make a call here to del VS.
    #PTP: do we need to del a VS if we can still use it later without retraining
    #considering we can del a VS and still keep the model file is there a method in VS which can check and load the model
    def delVS(sensorID):
        pass
            
    def missingValue(self, sensorID, freq):
        t = threading.Thread(target=self._missingValue, args=(sensorID, freq,))
        t.start()   
        
    def _missingValue(self, sensorID, freq):
        if sensorID not in self.missedValues.keys():
            self.missedValues[sensorID] = freq
            self.no_of_misses[sensorID] = 0 # necessary to have separate counters for miss and fault because of reset condition
            return self.callVS(sensorID, 'm'), 0 #no result from first value as no decrease in freq| todo: change this if freq always starts with 1
        freq_difference = freq - self.missedValues[sensorID]
        self.missedValue[sensorID] = freq
        if freq_difference <= 0 and freq != 1 :
            self.no_of_misses[sensorID] = self.no_of_misses[sensorID] + 1
            return self.callVS(sensorID, 'm'), 1
        else:
            self.no_of_misses[sensorID] = 0
            return self.callVS(sensorID, 'm'), 0
    
    def update(self, sensorID, value):
        t = threading.Thread(target=self._update, args=(sensorID, value,))
        t.start()
        
    def _update(self, sensorID, value):
        if sensorID not in self.old_values.keys():
            self.old_values[sensorID] = value
            self.no_of_faults[sensorID] = 0
            self.createdVS[sensorID] = 0
            return self.callVS(sensorID, 'u'), 0 #skip if its the first value - No difference
        difference = value - self.old_value[sensorID]
        self.old_values[sensorID] = value
        #return 0 if normal return 1 if faulty
        if self.detectors[sensorID].detector(difference) == 'F':
            self.no_of_faults[sensorID] = self.no_of_faults[sensorID] + 1
            return self.callVS(sensorID, 'u'), 1
        else:
            self.no_of_faults[sensorID] = 0
            return self.callVS(sensorID, 'u'), 0
