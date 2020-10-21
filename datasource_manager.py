import logging
import threading

from ngsi_ld import broker_interface
from ngsi_ld import ngsi_parser
from ngsi_ld.ngsi_parser import NGSI_Type

logger = logging.getLogger('monitoring')


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

    def update(self, ngsi_data, sendIt=False):
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
        if sendIt:
            broker_interface.create_ngsi_entity(ngsi_data)

    def replace_attr(self, old_attr_id, new_attr, entity_id):
        # broker_interface.delete_ngsi_attribute(old_attr_id, entity_id) # remove the old attribute?
        broker_interface.add_ngsi_attribute(new_attr, entity_id)

    def remove_attr(self, entity_id, attr_id):
        broker_interface.delete_ngsi_attribute(attr_id, entity_id)

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
        if type(subid) == str and subid in self.subscriptions:
            subscription = self.subscriptions.pop(subid)
            broker_interface.del_subscription(subscription)
        elif type(subid) == dict:
            # maybe parameter is subscription dict
            broker_interface.del_subscription(subid)

    def del_all_subscriptions(self):
        for subid in list(self.subscriptions.keys()):
            self.del_subscription(subid)

    def get_subscriptions(self):
        return self.subscriptions

    def del_all_FD_subscriptions(self):
        all_subscriptions = broker_interface.get_all_subscriptions()
        logger.debug("Broker has " + str(len(all_subscriptions)) + " subscribtions at the moment")
        for subscription in all_subscriptions:
            id = subscription['id']
            logger.debug("Deleting subscription with ID " + id)
            if id.startswith("urn:ngsi-ld:Subscription:FD_"):
                self.del_subscription(subscription)
