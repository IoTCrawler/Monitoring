import dateutil.parser
import logging
from enum import Enum
import copy

logger = logging.getLogger('monitoring')


class NGSI_Type(Enum):
    StreamObservation = 1
    IoTStream = 2
    Sensor = 3
    Notification = 4
    ObservableProperty = 5
    QoI = 6

def resolve_prefixes(ngsi_data):
    if not '@context' in ngsi_data or len(ngsi_data['@context']) <= 1:
        return ngsi_data
    context_map = ngsi_data['@context'][1]
    copy_data = copy.deepcopy(ngsi_data)
    for key in ngsi_data:
        for prefix in context_map:
            p = prefix + ":"
            if type(ngsi_data[key]) == str and ngsi_data[key].startswith(p):
                copy_data[key] = copy_data[key].replace(p, context_map[prefix])
            if key.startswith(p):
                newkey = key.replace(p, context_map[prefix])
                copy_data[newkey] = copy_data[key]
                del copy_data[key]
    return copy_data


def get_type(ngsi_data):
    ngsi_type = ngsi_data['type']
    if ngsi_type in ("iot-stream:IotStream", "http://purl.org/iot/ontology/iot-stream#IotStream"):
        return NGSI_Type.IoTStream
    elif ngsi_type in ("iot-stream:StreamObservation", "http://purl.org/iot/ontology/iot-stream#StreamObservation"):
        return NGSI_Type.StreamObservation
    elif ngsi_type in ("sosa:Sensor", "http://www.w3.org/ns/sosa/Sensor"):
        return NGSI_Type.Sensor
    elif ngsi_type in ("sosa:ObservableProperty", "http://www.w3.org/ns/sosa/ObservableProperty"):
        return NGSI_Type.ObservableProperty
    elif ngsi_type in ("qoi:Quality", "https://w3id.org/iot/qoi#Quality"):
        return NGSI_Type.QoI
    elif ngsi_type in "Notification":
        return NGSI_Type.Notification


def get_url(ngsi_type):
    if ngsi_type == NGSI_Type.IoTStream:
        return "http://purl.org/iot/ontology/iot-stream#IotStream"
    elif ngsi_type == NGSI_Type.StreamObservation:
        return "http://purl.org/iot/ontology/iot-stream#StreamObservation"
    elif ngsi_type == NGSI_Type.Sensor:
        return "http://www.w3.org/ns/sosa/Sensor"
    elif ngsi_type == NGSI_Type.ObservableProperty:
        return "http://www.w3.org/ns/sosa/ObservableProperty"
    elif ngsi_type == NGSI_Type.QoI:
        return "https://w3id.org/iot/qoi#Quality"


def get_notification_entities(notification):
    try:
        return notification['data']
    except KeyError:
        return None


def get_observation_stream(observation):
    try:
        return observation['iot-stream:belongsTo']['object']
    except KeyError:
        try:
            return observation['http://purl.org/iot/ontology/iot-stream#belongsTo']['object']
        except KeyError:
            return None


def get_observation_value(observation):
    try:
        return observation['sosa:hasSimpleResult']['value']
    except KeyError:
        try:
            return observation['http://www.w3.org/ns/sosa/hasSimpleResult']['value']
        except KeyError:
            return None


def get_observation_timestamp(observation):
    try:
        return dateutil.parser.parse(observation['sosa:hasSimpleResult']['observedAt']).timestamp()
    except (TypeError, KeyError, dateutil.parser.ParserError):
        try:
            return dateutil.parser.parse(
                observation['http://www.w3.org/ns/sosa/hasSimpleResult']['observedAt']).timestamp()
        except (TypeError, KeyError, dateutil.parser.ParserError):
            # return None
            # added if sosa:resultTime is used instead of ngsi-ld observedAt
            return get_observation_resulttime(observation)


def get_observation_resulttime(observation):
    try:
        return dateutil.parser.parse(observation['sosa:resultTime']['value']).timestamp()
    except (TypeError, KeyError, dateutil.parser.ParserError):
        try:
            return dateutil.parser.parse(
                observation['http://www.w3.org/ns/sosa/resultTime']['value']).timestamp()
        except (TypeError, KeyError, dateutil.parser.ParserError):
            return None


def get_id(ngsi_data):
    try:
        return ngsi_data['id']
    except KeyError:
        return None, None


def get_IDandType(ngsi_data):
    try:
        return get_id(ngsi_data), get_type(ngsi_data)
    except KeyError:
        return None, None


def get_sensor_min(sensor):
    try:
        return sensor['qoi:min']['value']
    except KeyError:
        try:
            return sensor['https://w3id.org/iot/qoi#min']['value']
        except KeyError:
            return None


def get_sensor_max(sensor):
    try:
        return sensor['qoi:max']['value']
    except KeyError:
        try:
            return sensor['https://w3id.org/iot/qoi#max']['value']
        except KeyError:
            return None


def get_sensor_regexp(sensor):
    try:
        return sensor['qoi:regexp']['value']
    except KeyError:
        try:
            return sensor['https://w3id.org/iot/qoi#regexp']['value']
        except KeyError:
            return None


def get_sensor_valuetype(sensor):
    try:
        return sensor['qoi:valuetype']['value']
    except KeyError:
        try:
            return sensor['https://w3id.org/iot/qoi#valuetype']['value']
        except KeyError:
            return None


def get_sensor_updateinterval_and_unit(sensor):
    try:
        return sensor['qoi:updateinterval']['value'], sensor['qoi:updateinterval']['qoi:unit']['value']
    except KeyError:
        try:
            return sensor['https://w3id.org/iot/qoi#updateinterval']['value'], \
                   sensor['https://w3id.org/iot/qoi#updateinterval']['https://w3id.org/iot/qoi#unit']['value']
        except KeyError:
            return None, None


def get_sensor_observes(sensor):
    try:
        return sensor['sosa:observes']['object']
    except KeyError:
        try:
            return sensor['http://www.w3.org/ns/sosa/observes']['object']
        except KeyError:
            return None


def get_sensor_madeObservation(sensor):
    try:
        return sensor['sosa:madeObservation']['object']
    except KeyError:
        try:
            return sensor['http://www.w3.org/ns/sosa/madeObservation']['object']
        except KeyError:
            return None


def get_stream_generatedBy(stream):
    try:
        return stream['iot-stream:generatedBy']['object']
    except KeyError:
        try:
            return stream['http://purl.org/iot/ontology/iot-stream#generatedBy']['object']
        except KeyError:
            return None


def get_obsproperty_label(obsproperty):
    try:
        return obsproperty['rdfs:label']['value']
    except KeyError:
        try:
            return obsproperty['http://www.w3.org/2000/01/rdf-schema#label']['value']
        except KeyError:
            return None


def update_stream_hasQuality(stream, qoiId):
    if 'hasQuality' in stream:
        stream['hasQuality']['object'] = qoiId
    elif 'https://w3id.org/iot/qoi#hasQuality' in stream:
        stream['https://w3id.org/iot/qoi#hasQuality']['object'] = qoiId
    else:
        hasQoi_ngsi = {
            "qoi:hasQuality": {
                "type": "Relationship",
                "object": qoiId
            },
            "@context": [
                "http://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld", {
                    "qoi": "https://w3id.org/iot/qoi#"
                }
            ]
        }
        stream.update(hasQoi_ngsi)
