import datetime
import json
import logging
import uuid
import threading
import sys

from flask import Flask, redirect, render_template, url_for, request, Blueprint, flash, Response

import ngsi_ld.ngsi_parser
from configuration import Config
from ngsi_ld.ngsi_parser import NGSI_Type
from other.exceptions import BrokerError
from other.logging import DequeLoggerHandler
from sensor import Sensor
from datasource_manager import DatasourceManager
from ngsi_ld.broker_interface import get_entity

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
sensorToObservationMap = {}
qualityToSensorMap = {}


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
    logger.debug("callback sensor called" + str(data))
    print("callback sensor called" + str(data))

    ngsi_type = ngsi_ld.ngsi_parser.get_type(data)

    # check if notification which might contain other entities
    if ngsi_type is NGSI_Type.Notification:
        data = ngsi_ld.ngsi_parser.get_notification_entities(data)
    else:
        data = [data]
    return handle_new_sensor(data)

def handle_new_sensor(data):
    for entity in data:
        s = Sensor(entity)
        sensorID = s.ID()
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
                    stream = get_entity(iotstreamID)
                    if stream:
                        qualityID = stream['https://w3id.org/iot/qoi#hasQuality']['object']
                        qualityToSensorMap[qualityID] = s
            except KeyError:
                logger.debug("could not determine the ID of the Quality for sensor " + sensorID + ". Detection of missing values will not be possible")
        else:
            logger.debug("FaultDetection not enabled for " + sensorID)

    return Response('OK', status=200)

@bp.route('/callback/observation', methods=['POST'])
def callback_observation():
    data = request.get_json()
    # check if notification which might contain other entities
    if ngsi_type is NGSI_Type.Notification:
        data = ngsi_ld.ngsi_parser.get_notification_entities(data)
    else:
        data = [data]

    for entity in data:
        streamObservationID = entity['id']
        value = entity['http://www.w3.org/ns/sosa/hasSimpleResult']['value']
        if streamObservationID in sensorToObservationMap:
            threading.Thread(target=_call_FD_update, args=(sensorToObservationMap[streamObservationID].ID(), value)).start()

    return Response('OK', status=200)

def _call_FD_update(sensorID, value):
    createOrDelecteVS, isValueFaulty = faultDetection.update(sensorID, value)
    if isValueFaulty:
        faultRecovery.update(sensorID, value)
        if createOrDelecteVS == 1:
            # TODO: call VS creater
            pass
    if createOrDelecteVS == 2:
        # TODO: call VS creator to remove VS
        pass

# required to get to qoi:Frequency
@bp.route('/callback/qoi', methods=['POST'])
def callback_qoi():
    data = request.get_json()
    # check if notification which might contain other entities
    if ngsi_type is NGSI_Type.Notification:
        data = ngsi_ld.ngsi_parser.get_notification_entities(data)
    else:
        data = [data]

    for entity in data:
        qoiID = entity['id']
        if qoiID in qualityToSensorMap:
            value = entity['https://w3id.org/iot/qoi#frequency']['https://w3id.org/iot/qoi#hasRatedValue']['value']
            thread.Thread(target=_call_FD_missingValue, args=(qualityToSensorMap[qoiID].ID(), value)).start()
    return Response('OK', status=200)

def _call_FD_missingValue(sensorID, freq):
    createOrDelecteVS, isValueMissing = faultDetection.missingValue(sensorID, freq)
    if isValueMissing:
        faultRecovery.update(sensorID, None)
        if createOrDelecteVS == 1:
            # call VS creater
            pass
    elif createOrDelecteVS == 2:
        # call VS creater to delete
        pass

# TODO: remove this blueprint???
@bp2.route('/', methods=['GET'])
def status():
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

    # datasourceManager.del_all_FD_subscriptions()
    # sys.exit(0)
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
    datasourceManager.initialise(datasourceManagerInitialised)
    app.run(host=Config.getEnvironmentVariable('FD_HOST'), port=int(Config.getEnvironmentVariable('FD_PORT')), debug=False)
    datasourceManager.del_all_subscriptions()
