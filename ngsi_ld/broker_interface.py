import threading
import requests
import logging
import json
import uuid

from configuration import Config
from ngsi_ld.subscription import Subscription
from ngsi_ld import ngsi_parser

logger = logging.getLogger('monitoring')

headers = {}
headers.update({'content-type': 'application/ld+json'})
headers.update({'accept': 'application/ld+json'})

# returns the label of a ObservableProperty identified by the its ID
# input: propertyID - the ID of the ObservableProperty as string
# output: the label as string
def get_observable_property_label(propertyID):
    """
    Get the label for an ObservableProperty.
    """
    try:
        server_url = '{}/ngsi-ld/v1/entities/{}'.format(Config.getEnvironmentVariable('NGSI_ADDRESS'), propertyID)
        r = requests.get(server_url, headers=headers)
        if r.status_code != 200:
            logger.error("Error gettign property label: " + str(r.status_code))
            return None
        else:
            d = r.json()
            if not "http://www.w3.org/2000/01/rdf-schema#label" in d:
                return None
            label = d["http://www.w3.org/2000/01/rdf-schema#label"]
            if not "value" in label:
                return None
            label = label["value"]
            return label
    except Exception as e:
        logger.error(e)
        return None


def find_neighbor_sensors(sensorID, propertyLabel, latitude, longitude, maxDistance):
    """
    input: lat, lng of desired location
            propertyLabel ObservalbeProperty by label; if None search for all labels
            maxDistance maximum distance of correlating sensors
    output: instance of Reply with data = [NGSI-LD code for a sensor]

    2 step approach: 1. collect all ObservableProperty IDs and 2. get all sensors in the area of intereset

    http://metadata-repository-scorpiobroker.35.241.228.250.nip.io/ngsi-ld/v1/entities/?type=http://www.w3.org/ns/sosa/Sensor/ObservableProperty&q=http://www.w3.org/2000/01/rdf-schema%23label==%22humidity%22
    http://metadata-repository-scorpiobroker.35.241.228.250.nip.io/ngsi-ld/v1/entities?type=http://www.w3.org/ns/sosa/Sensor&georel=near;maxDistance==200000&geometry=Point&coordinates=[52,8]&q=http://www.w3.org/ns/sosa/observes==urn:ngsi-ld:ObservableProperty:B4:E6:2D:8A:20:DD:Humidity
    """


    try:
        sensors = []
        if not propertyLabel:
            server_url = '{}/ngsi-ld/v1/entities/?type=http://www.w3.org/ns/sosa/ObservableProperty'.format(Config.getEnvironmentVariable('NGSI_ADDRESS'))
        else:
            server_url = '{}/ngsi-ld/v1/entities/?type=http://www.w3.org/ns/sosa/ObservableProperty&q=http://www.w3.org/2000/01/rdf-schema%23label==%22{}%22'.format(Config.getEnvironmentVariable('NGSI_ADDRESS'), propertyLabel)
        r = requests.get(server_url, headers=headers)
        # print("loaded:", response.geturl())
        if r.status_code != 200: # can this happen? seems urlopen throws an exception if not successful
            logger.error("Error getting ObservableProperty IDs: " + str(r.status_code))
            return None
        else:
            d = r.json()
            op_ids = []
            for op in d:
                if "id" in op:
                    op_ids.append(op['id'])
            # now load all the sensors with the IDs found
            print("property ids:", op_ids)
            for i in op_ids:
                server_url = '{}/ngsi-ld/v1/entities?type=http://www.w3.org/ns/sosa/Sensor&georel=near;maxDistance=={}&geometry=Point&coordinates=[{},{}]&q=http://www.w3.org/ns/sosa/observes=={}'.format(Config.getEnvironmentVariable('NGSI_ADDRESS'), maxDistance, latitude, longitude, i)
                r = requests.get(server_url, headers=headers)
                if r.status_code != 200: # can this happen? seems urlopen throws an exception if not successful
                    logger.error("Error getting ObservableProperty IDs: " + str(r.status_code))
                    return None
                d = r.json()
                for s in d:
                    if s['id'] != sensorID:
                        sensors.append(s)
        return sensors

    except Exception as e:
        logger.error(e)
        return None


# this method is mainly for testing etc as subscriptions are lost during restart,
# in addition ngrok won't fit for old subscriptions
def get_active_subscriptions(sublist):
    t = threading.Thread(target=_get_active_subscriptions, args=(sublist,))  # put into thread to not block server
    t.start()


def _get_active_subscriptions(subscriptions):
    # get old subscriptions for fault detection (with our callback url)
    # server_url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/subscriptions/"
    server_url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/subscriptions/"
    try:
        r = requests.get(server_url, headers=headers)
        if r.status_code == 200:
            if isinstance(r.json(), list):
                for data in r.json():
                    handlejsonsubscription(data, Config.getEnvironmentVariable('NGSI_ADDRESS'), subscriptions)
            if isinstance(r.json(), dict):
                handlejsonsubscription(r.json(), Config.getEnvironmentVariable('NGSI_ADDRESS'), subscriptions)
        else:
            logger.error("Error getting active subscriptions: " + r.text + str(r.status_code))
    except Exception as e:
        logger.error("Error getting active subscriptions: " + str(e))


def handlejsonsubscription(data, address, subscriptions):
    try:
        if data['notification']['endpoint']['uri'] == Config.getEnvironmentVariable('FD_CALLBACK'):
            sub = Subscription(data['id'], address, data)
            subscriptions[sub.id] = sub
            logger.info("Found active subscription: " + str(data))
        else:
            logger.info("not our subscription")
    except KeyError:
        return None


def initialise_subscriptions(sublist, subscriptionTypes):
    t = threading.Thread(target=_initialise_subscriptions,
                         args=(sublist, subscriptionTypes,))  # put into thread to not block server
    t.start()


def _initialise_subscriptions(subscriptions, subscriptionTypes):
    # first get active subscriptions
    _get_active_subscriptions(subscriptions)

    # iterate list and check for IotStream, StreamObservation, Sensor subscription, if not found subscribe
    for t in subscriptionTypes:
        subscribe = True
        for key, value in subscriptions.items():
            sub = value.subscription
            try:
                if ngsi_parser.get_type(sub['entities'][0]) is t:
                    # it is of type IotStream, check if it is our endpoint
                    if sub['notification']['endpoint']['uri'] == Config.getEnvironmentVariable('FD_CALLBACK'):
                        logger.debug("Subscription for " + str(t) + " already existing!")
                        subscribe = False
                        break
            except KeyError:
                pass
        if subscribe:
            logger.debug("Initialise system with subscription for " + str(t))
            _subscribe_forTypeId(t, None, subscriptions)


def add_subscription(subscription, subscriptionlist):
    t = threading.Thread(target=_add_subscription, args=(subscription, subscriptionlist))
    t.start()


def _add_subscription(subscription, subscriptions):
    # subscribe to ngsi-ld endpoint
    sub = Subscription(subscription['id'], Config.getEnvironmentVariable('NGSI_ADDRESS'), subscription)

    if ngsi_add_subscription(subscription) is not None:
        subscriptions[sub.id] = sub


def ngsi_add_subscription(subscription):
    # server_url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/subscriptions/"
    server_url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/subscriptions/"
    r = requests.post(server_url, json=subscription, headers=headers)
    logger.info("Adding subscription: " + str(r.status_code) + " " + r.text)
    if r.status_code != 201:
        logger.debug("error creating subscription: " + r.text)
        return None
    return r.text


def del_subscription(subscription):
    t = threading.Thread(target=_del_subscription, args=(subscription,))
    t.start()


def _del_subscription(subscription):
    # server_url = "http://" + subscription.address + "/ngsi-ld/v1/subscriptions/"
    server_url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/subscriptions/"
    if type(subscription) == dict:
        id = subscription['id']
    else:
        id = subscription.id
    server_url += id
    r = requests.delete(server_url, headers=headers)
    logger.debug("deleting subscription " + id + ": " + r.text)


def add_ngsi_attribute(ngsi_msg, eid):
    t = threading.Thread(target=_add_ngsi_attribute, args=(ngsi_msg, eid,))
    t.start()


def _add_ngsi_attribute(ngsi_msg, eid):
    try:
        logger.debug("Add ngsi attribute to entity " + eid + ":" + str(ngsi_msg))
        # url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + eid + "/attrs/"
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + eid + "/attrs/"
        r = requests.post(url, json=ngsi_msg, headers=headers)
        if r.status_code != 204 and r.status_code != 207:
            logger.error("Adding attribute faild. Status code = " + str(r.status_code))
            # requests.patch(url, json=ngsi_msg, headers=headers)
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while adding attribute to ngsi entity" + str(e))

def delete_ngsi_attribute(attr_id, eid):
    t = threading.Thread(target=_delete_ngsi_attribute, args=(attr_id, eid,))
    t.start()


def _delete_ngsi_attribute(attr_id, eid):
    try:
        logger.debug("Delete ngsi attribute to entity " + eid + " : " + attr_id)
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + eid + "/attrs/" + attr_id
        r = requests.delete(url, headers=headers)
        if r.status_code != 204:
            logger.error("Deleting attribute faild. Status code = " + str(r.status_code))
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while adding attribute to ngsi entity" + str(e))

def create_ngsi_entity(ngsi_msg):
    t = threading.Thread(target=_create_ngsi_entity, args=(ngsi_msg,))
    t.start()


def _create_ngsi_entity(ngsi_msg):
    try:
        logger.debug("Save entity to ngsi broker: " + str(ngsi_msg))
        # url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/"
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/"
        # print(url)
        r = requests.post(url, json=ngsi_msg, headers=headers)
        if r.status_code == 409:
            logger.debug("Entity exists, patch it")
            _patch_ngsi_entity(ngsi_msg)
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while creating ngsi entity" + str(e))


def patch_ngsi_entity(ngsi_msg):
    t = threading.Thread(target=_patch_ngsi_entity, args=(ngsi_msg,))
    t.start()


def _patch_ngsi_entity(ngsi_msg):
    try:
        # for updating entity we have to delete id and type, first do copy if needed somewhere else
        ngsi_msg_patch = dict(ngsi_msg)
        ngsi_msg_patch.pop('id')
        ngsi_msg_patch.pop('type', None)
        # url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + ngsi_msg[
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + ngsi_msg[
            'id'] + "/attrs"
        r = requests.patch(url, json=ngsi_msg_patch, headers=headers)
        logger.debug("Entity patched: " + str(r.status_code))
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while patching ngsi entity" + str(e))


def get_entity_updateList(entityid, entitylist):
    t = threading.Thread(target=_get_entity_updateList, args=(entityid, entitylist))
    t.start()


def _get_entity_updateList(entityid, entitylist):
    entity = get_entity(entityid)
    if entity:
        entitylist[entityid] = entity


def get_entity(entitiyid):
    try:
        # url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + entitiyid
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/" + entitiyid
        logger.debug("loading: " + url)
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            logger.error("Error requesting entity " + entitiyid + ": " + r.text)
            return None
        return r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while getting entity " + entitiyid + ": " + str(e))


def get_entities(entitytype, limit, offset):
    try:
        # url = "http://" + Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/"
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/"
        params = {'type': entitytype, 'limit': limit, 'offset': offset}
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != 200:
            logger.error("Error requesting entities of type " + entitytype + ": " + r.text)
            return None
        return r.json()
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while getting entities of type " + entitytype + ": " + str(e))


def get_all_entities(entitytype):
    if type(entitytype) is ngsi_parser.NGSI_Type:
        entitytype = ngsi_parser.get_url(entitytype)
    limit = 50
    offset = 0
    result = []
    while True:
        tmpresult = get_entities(entitytype, limit, offset)
        if not tmpresult:
            break
        result.extend(tmpresult)
        if len(tmpresult) < limit:
            break
        offset += 50
    return result

def get_all_subscriptions():
    limit = 50
    offset = 0
    subs = []
    url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/subscriptions/"
    try:
        while True:
            params = {'limit': limit, 'offset': offset}
            r = requests.get(url, headers=headers, params=params)
            if r.status_code != 200:
                logger.error("Error requesting entities of type " + entitytype + ": " + r.text)
                break
            tmpresult = r.json()
            subs.extend(tmpresult)
            if len(tmpresult) < limit:
                break
            offset += 50
            # TODO: This leads to an endless loop - why?
            break
        return subs
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while getting entities of type " + entitytype + ": " + str(e))



def subscribe_forTypeId(ngsi_type, entityId, sublist):
    t = threading.Thread(target=_subscribe_forTypeId, args=(ngsi_type, entityId, sublist))
    t.start()


def _subscribe_forTypeId(ngsi_type, entityId, sublist):
    logger.debug("Subscribe for " + str(ngsi_type) + " " + str(entityId))
    # check if subscription already in sublist
    # solution is not optimal... but no other option at the moment
    if entityId:
        for key, value in sublist.items():
            sub = value.subscription
            try:
                tmposid = sub['entities'][0]['id']
                if tmposid == entityId:
                    logger.debug("Subscription for " + tmposid + " already existing!")
                    return
            except KeyError:
                pass

    endpoint_extension = ""
    # create subscription
    if ngsi_type is ngsi_parser.NGSI_Type.Sensor:
        filename = 'static/json/subscription_sensor.json'
        endpoint_extension = "/callback/sensor"
    elif ngsi_type is ngsi_parser.NGSI_Type.IoTStream:
        filename = 'static/json/subscription_iotstream.json'
    elif ngsi_type is ngsi_parser.NGSI_Type.StreamObservation:
        filename = 'static/json/subscription_streamobservation.json'
        endpoint_extension = "/callback/observation"
    elif ngsi_type is ngsi_parser.NGSI_Type.ObservableProperty:
        filename = 'static/json/subscription_observableproperty.json'
    elif ngsi_type is ngsi_parser.NGSI_Type.QoI:
        filename = 'static/json/subscription_qoi.json'
        endpoint_extension = "/callback/qoi"
    else:
        logger.debug("No subscription file found for:" + str(ngsi_type))
        return

    with open(filename) as jFile:
        subscription = json.load(jFile)
        subscription['id'] = subscription['id'] + str(uuid.uuid4())
        # replace callback
        subscription['notification']['endpoint']['uri'] = Config.getEnvironmentVariable('FD_CALLBACK') + "/monitoring" + endpoint_extension
        # set entity to subscribe to
        if entityId:
            subscription['entities'][0]['id'] = entityId
        _add_subscription(subscription, sublist)

def find_stream(qualityid):
    try:
        url = Config.getEnvironmentVariable('NGSI_ADDRESS') + "/ngsi-ld/v1/entities/"
        params = {'type': 'http://purl.org/iot/ontology/iot-stream#IotStream', 'q': 'https://w3id.org/iot/qoi#hasQuality==' + qualityid}
        r = requests.get(url, headers=headers, params=params)
        if r.status_code != 200:
            logger.error("Error finding streamobservation for stream " + qualityid + ": " + r.text)
            return None
        return r.json() # list of entities
    except requests.exceptions.ConnectionError as e:
        logger.error("Error while finding streamobservation for stream " + qualityid + ": " + str(e))

def handleNewSensor(sensorId, sensors, observableproperties, subscriptions):
    # GET for sensor
    sensor = get_entity(sensorId)
    if sensor:
        sensors[sensorId] = sensor

        # GET for obsproperty(sensor)
        observablepropertyId = ngsi_parser.get_sensor_observes(sensor)
        if observablepropertyId:
            observableproperty = get_entity(observablepropertyId)
            if observableproperty:
                observableproperties[observablepropertyId] = observableproperty

        # subscriptions disabled as we subscribe for all sensors and observations
        # SUB for streamobservation(sensor)
        # streamobservationId = ngsi_parser.get_sensor_madeObservation(sensor)
        # _subscribe_forTypeId(ngsi_parser.NGSI_Type.StreamObservation, streamobservationId, subscriptions)
        # SUB for sensor
        # _subscribe_forTypeId(ngsi_parser.NGSI_Type.Sensor, sensorId, subscriptions)


# for testing purposes
if __name__ == "__main__":
    print(get_all_entities('http://purl.org/iot/ontology/iot-stream#IotStream'))
