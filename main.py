import datetime
import json
import logging
import uuid
import threading
import sys

from flask import Flask, redirect, render_template, url_for, request, Blueprint, flash, Response

import ngsi_ld.ngsi_parser
from configuration import Config
from ngsi_ld.ngsi_parser import NGSI_Type, resolve_prefixes
from other.exceptions import BrokerError
from other.logging import DequeLoggerHandler
from other.utils import makeStreamObservation, ObservationCache, IMPUTATION_PROPERTY_NAME, SIMPLE_RESULT_PROPERTY_NAME
from other.vs_creater_interface import replaceBrokenSensor, stopVirtualSensor
from sensor import Sensor
from datasource_manager import DatasourceManager
from ngsi_ld.broker_interface import get_entity, find_stream

#just for testing - remove later
from ngsi_ld.broker_interface import find_neighbor_sensors, get_observable_property_label

from fault_recovery.fault_recovery import FaultRecovery
from fault_detection.FaultDetection import FaultDetection

# Configure logging
logger = logging.getLogger('monitoring')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%dT%H:%M:%SZ')

file_handler = logging.FileHandler('monitoring.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

deque_handler = DequeLoggerHandler(int(Config.get('logging', 'maxlogentries')))
deque_handler.setLevel(logging.DEBUG)
deque_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(deque_handler)
logger.info("logger ready")

bp = Blueprint('monitoring', __name__, static_url_path='', static_folder='static', template_folder='html')
bp2 = Blueprint('', __name__, static_url_path='', static_folder='static',
                template_folder='html')  # second blueprint for return liveness probe for kubernets

datasourceManager = DatasourceManager()
faultDetection = FaultDetection()
faultRecovery = FaultRecovery()
sensorsMap = {}
sensorToObservationMap = {}
# qualityToSensorMap = {}
streamToSensorMap = {}
qualityToStreamMap = {}

imputedStreamObservationIDs = [] # list of observation IDs with IMPUTATION_PROPERTY_NAME attributes


def format_datetime(value):
    if isinstance(value, float):
        value = datetime.datetime.fromtimestamp(value)
    if value:
        return value.strftime('%Y-%m-%d %H:%M:%SZ')  # added space instead of 'T' to enable line break
    return None


@bp.route('/')
@bp.route('/index')
def index():
    return render_template("index.html")


# @bp.route('/showsubscriptions', methods=['GET', 'POST'])
# def showsubscriptions():
#     subscriptions = datasourceManager.get_subscriptions()
#     return render_template('subscriptions.html', subscriptions=subscriptions.values(), id=str(uuid.uuid4()),
#                            endpoint=Config.getEnvironmentVariable('FD_CALLBACK'))


# @bp.route('/log', methods=['GET'])
# def showlog():
#     return render_template('log.html', logmessages=deque_handler.get_entries(),
#                            maxentries=int(Config.get('logging', 'maxlogentries')))

@bp.route('/running', methods=['GET'])
def showrunning():
    return "running"


# @bp.route('/addsubscription', methods=['POST'])
# def addsubscription():
#     subscription = request.form.get('subscription')
#     try:
#         datasourceManager.add_subscription(json.loads(subscription))
#     except BrokerError as e:
#         flash('Error while adding subscription:' + str(e))
#     return redirect(url_for('.showsubscriptions'))
#
#
# @bp.route('/getsubscriptions', methods=['POST'])
# def getsubscriptions():
#     datasourceManager.get_active_subscriptions()
#     return redirect(url_for('.showsubscriptions'))
#
#
# @bp.route('/deleteallsubscriptions', methods=['POST'])
# def deleteallsubscriptions():
#     datasourceManager.del_all_subscriptions()
#     return redirect(url_for('.showsubscriptions'))
#
#
# @bp.route('/deletesubscription', methods=['POST'])
# def deletesubscription():
#     subid = request.form.get('subid')
#     if subid is not None:
#         logger.info("Delete subscription: " + subid)
#         datasourceManager.del_subscription(subid)
#     return redirect(url_for('.showsubscriptions'))
#
#
# @bp.route('/showdatasources', methods=['GET'])
# def showdatasources():
#     datasources = []
#     for stream_id, stream in datasourceManager.streams.items():
#         class datasource:  # local class to be returned to html page
#             pass
#
#         datasource.stream_id = stream_id
#
#         # get sensor for stream
#         sensorId = ngsi_ld.ngsi_parser.get_stream_generatedBy(stream)
#         sensor = datasourceManager.get_sensor(sensorId)
#
#         # get observation for sensor
#         if sensor:
#             observationId = ngsi_ld.ngsi_parser.get_sensor_madeObservation(sensor)
#             observation = datasourceManager.get_observation(observationId)
#
#             if observation:
#                 datasource.observation = json.dumps(observation, indent=2)
#                 datasource.observedat = ngsi_ld.ngsi_parser.get_observation_timestamp(observation)
#
#             obspropertyId = ngsi_ld.ngsi_parser.get_sensor_observes(sensor)
#             obsproperty = datasourceManager.get_observableproperty(obspropertyId)
#             datasource.obsproperty = json.dumps(obsproperty, indent=2)
#
#         datasource.stream = json.dumps(stream, indent=2)
#         datasource.sensor = json.dumps(sensor, indent=2)
#         datasources.append(datasource)
#     return render_template('datasources.html', datasources=datasources)


@bp.route('/callback/sensor', methods=['POST'])
def callback():
    data = request.get_json()
    # logger.debug("callback sensor called" + str(data))
    # print("callback sensor called" + str(data))

    ngsi_type = ngsi_ld.ngsi_parser.get_type(data)

    # check if notification which might contain other entities
    if ngsi_type is NGSI_Type.Notification:
        data = ngsi_ld.ngsi_parser.get_notification_entities(data)
    else:
        data = [data]
    return handle_new_sensor(data)

def handle_new_sensor(data):
    for entity in data:
        entity = resolve_prefixes(entity)
        s = Sensor(entity)
        sensorID = s.ID()
        sensorsMap[sensorID] = s
        if s.isFaultDetectionEnabled():
            logger.debug("start FD for sensor: " + sensorID)
            datasourceManager.update(entity)
            faultDetection.newSensor(entity)
            faultRecovery.newSensor(sensorID, entity)
            sensorToObservationMap[s.streamObservationID()] = s

            so = get_entity(s.streamObservationID())
            try:
                if so:
                    iotstreamID = so['http://purl.org/iot/ontology/iot-stream#belongsTo']['object']
                    streamToSensorMap[iotstreamID] = s
                else:
                    logger.debug("Could not get Stream entity " + s.streamObservationID())
            except KeyError:
                logger.debug("could not determine the ID of the Quality for sensor " + sensorID + ". Detection of missing values will not be possible")
        else:
            # logger.debug("FaultDetection not enabled for " + sensorID)
            pass

    return Response('OK', status=200)

@bp.route('/callback/observation', methods=['POST'])
def callback_observation():
    data = request.get_json()
    # check if notification which might contain other entities
    ngsi_type = ngsi_ld.ngsi_parser.get_type(data)
    if ngsi_type is NGSI_Type.Notification:
        data = ngsi_ld.ngsi_parser.get_notification_entities(data)
    else:
        data = [data]

    for entity in data:
        entity = resolve_prefixes(entity)
        if IMPUTATION_PROPERTY_NAME in entity: # no need to process our own StreamObservation
            print("IMPUTED ENTITY:", entity)
            continue
        streamObservationID = entity['id']
        if streamObservationID in sensorToObservationMap:
            value = entity['http://www.w3.org/ns/sosa/hasSimpleResult']['value']
            sensorID = sensorToObservationMap[streamObservationID].ID()
            ObservationCache.update(sensorID, value)
            threading.Thread(target=_call_FD_update, args=(streamObservationID, sensorID, value)).start()

    return Response('OK', status=200)

def _call_FD_update(streamObservationID, sensorID, value):
    createOrDeleteVS, isValueFaulty = faultDetection.update(sensorID, value)
    logger.debug("FD verdict:  createOrDeleteVS = %d, isValueFaulty = %d" % (createOrDeleteVS, isValueFaulty))

    if isValueFaulty:
        # TODO: callback for the FR? - requires to pass the sensor object, not the sensorID
        sensor = sensorToObservationMap[streamObservationID]
        imputeValue = faultRecovery.update(sensorID, value)
        if imputeValue:
            newStremObservation = makeStreamObservation(sensor, imputeValue)
            # send to broker
            datasourceManager.replace_attr(SIMPLE_RESULT_PROPERTY_NAME, newStremObservation, streamObservationID)
            imputedStreamObservationIDs.append(streamObservationID)
        if createOrDeleteVS == 1:
            replaceBrokenSensor(sensorID) # through virtual sensor

    elif streamObservationID in imputedStreamObservationIDs:
        # sensor provide a new and valid observation, remove the imputed one
        datasourceManager.remove_attr(streamObservationID, IMPUTATION_PROPERTY_NAME)
        imputedStreamObservationIDs.remove(streamObservationID)

    if createOrDeleteVS == 2:
        stopVirtualSensor(sensorID)

def _FR_callback(sensor, imputeValue):
    if imputeValue:
        newStremObservation = makeStreamObservation(sensor, imputeValue)
        datasourceManager.update(newStremObservation)

# required to get to qoi:Frequency
@bp.route('/callback/qoi', methods=['POST'])
def callback_qoi():
    data = request.get_json()
    # check if notification which might contain other entities
    ngsi_type = ngsi_ld.ngsi_parser.get_type(data)
    if ngsi_type is NGSI_Type.Notification:
        data = ngsi_ld.ngsi_parser.get_notification_entities(data)
    else:
        data = [data]

    for entity in data:
        entity = resolve_prefixes(entity)
        if not 'https://w3id.org/iot/qoi#frequency' in entity:
            # the meta-data for this sensor did not specify an update interval
            # impossible to dermine if a observation is missing
            continue
        qoiID = entity['id']
        sensorID = None
        if qoiID in qualityToStreamMap:
            streamID = qualityToStreamMap[qoiID]
            if streamID in streamToSensorMap:
                sensor = streamToSensorMap[streamID]
                sensor.setStreamID(streamID)
                sensorID = sensor.ID()
            else:
                logger.error("no sensor known having stream " + streamID + " with QoI " + qoiID)
                continue
        else:
            logger.debug("searching StreamID for Quality with ID " + qoiID)
            streams = find_stream(qoiID)
            if streams and len(streams) >= 1:
                streamID = streams[0]['id']
                if streamID in streamToSensorMap:
                    sensor = streamToSensorMap[streamID]
                    sensor.setStreamID(streamID)
                    sensorID = sensor.ID()
                    qualityToStreamMap[qoiID] = streamID
                else:
                    logger.error("no sensor known having stream " + streamID)
                    continue
            elif streams and len(streams) > 1:
                logger.warning("multiple streams have Quality with ID " + qoiID)
            else:
                logger.error("no stream found having quality " + qoiID)
                continue

        try:
            if sensorID:
                value = entity['https://w3id.org/iot/qoi#frequency']['https://w3id.org/iot/qoi#hasRatedValue']['value']
                threading.Thread(target=_call_FD_missingValue, args=(qoiID, sensorID, value)).start()
        except KeyError:
            logger.error("QoI notification has no Frequency")

    return Response('OK', status=200)

def _call_FD_missingValue(qualityID, sensorID, freq):
    createOrDeleteVS, isValueMissing = faultDetection.missingValue(sensorID, freq)
    logger.debug("FD verdict:  createOrDeleteVS = %d, isValueMissing = %d" % (createOrDeleteVS, isValueMissing))
    sensor = sensorsMap[sensorID]
    if isValueMissing:
        imputeValue = faultRecovery.update(sensorID, None)
        if imputeValue != None:
            newStremObservation = makeStreamObservation(sensor, imputeValue)
            logger.debug("will impute value")
            datasourceManager.replace_attr(SIMPLE_RESULT_PROPERTY_NAME, newStremObservation, sensor.streamObservationID())
            imputedStreamObservationIDs.append(sensor.streamObservationID())
        else:
            logger.debug("FR did not provide imputable value")
        if createOrDeleteVS == 1:
            # call VS creater
            replaceBrokenSensor(sensorID) # through virtual sensor

    elif sensor.streamObservationID() in imputedStreamObservationIDs: # The Monitoring should receive the Observation before
                                                                      # so this should never be true, but in case Monitoring missed it.
        # sensor provide a new and valid observation, remove the imputed one
        datasourceManager.remove_attr(sensor.streamObservationID(), IMPUTATION_PROPERTY_NAME)
        imputedStreamObservationIDs.remove(sensor.streamObservationID())

    if createOrDeleteVS == 2:
        # call VS creater to delete
        stopVirtualSensor(sensorID)

# TODO: remove this blueprint???
@bp2.route('/', methods=['GET'])
def status2():
    return "running"
    # return redirect(url_for('semanticenrichment.index'))


@bp.route('/status', methods=['GET'])
def status():
    return "running"


app = Flask(__name__)
app.secret_key = 'e3645c25b6d5bf67ae6da68c824e43b530e0cb43b0b9432c'
app.register_blueprint(bp, url_prefix='/monitoring')
app.register_blueprint(bp2, url_prefix='/')
app.jinja_env.filters['datetime'] = format_datetime

def datasourceManagerInitialised():

    # TODO: subscribe to get notified for new sensor registrations and StreamObservations
    #       instanciate FD and FR for each stream
    #       start fault recovery traning for each new stream
    sensors = datasourceManager.sensors
    sensor_list = []
    for sID in sensors:
        # print("found sensor", sID)
        # print(sensors[sID])
        sensor_list.append(sensors[sID])
    handle_new_sensor(sensor_list)

if __name__ == "__main__":
    # label = get_observable_property_label("urn:ngsi-ld:ObservableProperty:AvailableParkingSpaces")
    # print(label)
    # sensors = find_neighbor_sensors("urn:ngsi-ld:Sensor:ora18", label, -1.127544427, 37.99218475, 2000)
    # print(sensors)
    #
    #
    # # datasourceManager.del_all_FD_subscriptions()

    # testing BME FR
    # urn_ngsi-ld_Sensor_parking101
    e = """{
  "id" : "urn:ngsi-ld:Sensor:parking101",
  "type" : "http://www.w3.org/ns/sosa/Sensor",
  "http://www.w3.org/ns/sosa/observes" : {
    "type" : "Relationship",
    "object" : "urn:ngsi-ld:ObservableProperty:AvailableParkingSpaces"
  },
  "location" : {
    "type" : "GeoProperty",
    "value" : {
      "type" : "Point",
      "coordinates" : [ -1.1336517, 37.9894006 ]
    }
  },
  "@context" : [ "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld" ]
}"""
    from fault_recovery.fault_recovery_bme import FaultRecoveryBME
    from fault_recovery.fault_recovery_mcmc import FaultRecoveryMCMC
    fr = FaultRecoveryMCMC()
    # fr = FaultRecoveryBME()
    fr.newSensor("urn:ngsi-ld:Sensor:parking101", e)
    input("trained")
    dt = datetime.datetime.now()
    ObservationCache.update("urn:ngsi-ld:Sensor:parking102", 250.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking103", 240.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking104", 270.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking105", 210.0)
    fr.update("urn:ngsi-ld:Sensor:parking101", dt.isoformat())
    input("next")
    dt = dt.replace(minute=(dt.minute + 30) % 60)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking102", 150.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking103", 300.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking104", 210.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking105", 280.0)
    fr.update("urn:ngsi-ld:Sensor:parking101", dt.isoformat())
    input("next")
    dt = dt.replace(minute=(dt.minute + 30) % 60)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking102", 180.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking103", 250.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking104", 220.0)
    ObservationCache.update("urn:ngsi-ld:Sensor:parking105", 180.0)
    fr.update("urn:ngsi-ld:Sensor:parking101", dt.isoformat())
    sys.exit(0)

    # real code starting here
    datasourceManager.initialise(datasourceManagerInitialised)
    app.run(host=Config.getEnvironmentVariable('FD_HOST'), port=int(Config.getEnvironmentVariable('FD_PORT')), debug=False)
    datasourceManager.del_all_subscriptions()
