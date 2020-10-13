import logging
import threading

from ngsi_ld import broker_interface
from ngsi_ld import ngsi_parser
from ngsi_ld.ngsi_parser import NGSI_Type

logger = logging.getLogger('faultdetection')


class DatasourceManager:

    def __init__(self):
        self.subscriptions = {}
        self.streams = {}
        self.sensors = {}
        self.observations = {}
        self.observableproperties = {}
        # self.initialise()

    def initialise(self, finishCallback=None):
        broker_interface.initialise_subscriptions(self.subscriptions,
                                                  # (NGSI_Type.IoTStream, NGSI_Type.Sensor, NGSI_Type.ObservableProperty))
                                                  (NGSI_Type.Sensor, NGSI_Type.StreamObservation, NGSI_Type.QoI))

        # get and notify for existing entities in a separate thread as this is blocking
        if finishCallback:
            for ngsi_type in [NGSI_Type.QoI, NGSI_Type.Sensor, NGSI_Type.StreamObservation]:
                self.initialise_entities(ngsi_type)
            finishCallback()
        else: # can be done asynchronous
            for ngsi_type in [NGSI_Type.QoI, NGSI_Type.Sensor, NGSI_Type.StreamObservation]:
                t = threading.Thread(target=self.initialise_entities, args=(ngsi_type,))
                t.start()

    def initialise_entities(self, ngsi_type):
        entities = broker_interface.get_all_entities(ngsi_type)
        logger.debug("There are " + str(len(entities)) + " existing " + str(ngsi_type))
        for entity in entities:
            logger.debug("Initialise entity " + ngsi_parser.get_id(entity))
            self.update(entity)

    def update(self, ngsi_data):
        ngsi_id, ngsi_type = ngsi_parser.get_IDandType(ngsi_data)
        # check type
        if ngsi_type is NGSI_Type.IoTStream:
            self.streams[ngsi_id] = ngsi_data
        elif ngsi_type is NGSI_Type.StreamObservation:
            self.observations[ngsi_id] = ngsi_data
        elif ngsi_type is NGSI_Type.Sensor:
            self.sensors[ngsi_id] = ngsi_data
        elif ngsi_type is NGSI_Type.ObservableProperty:
            self.observableproperties[ngsi_id] = ngsi_data

    def get_sensor(self, sensor_id):
        try:
            return self.sensors[sensor_id]
        except KeyError:
            return None

    def get_observation(self, observation_id):
        try:
            return self.observations[observation_id]
        except KeyError:
            return None

    def get_observableproperty(self, observableproperty_id):
        try:
            return self.observableproperties[observableproperty_id]
        except KeyError:
            return None

    def get_stream(self, stream_id):
        try:
            return self.streams[stream_id]
        except KeyError:
            return None

    def get_active_subscriptions(self):
        broker_interface.get_active_subscriptions(self.subscriptions)

    def add_subscription(self, subscription):
        broker_interface.add_subscription(subscription, self.subscriptions)

    def del_subscription(self, subid):
        subscription = self.subscriptions.pop(subid)
        broker_interface.del_subscription(subscription)

    def del_all_subscriptions(self):
        for subid in list(self.subscriptions.keys()):
            self.del_subscription(subid)

    def get_subscriptions(self):
        return self.subscriptions
