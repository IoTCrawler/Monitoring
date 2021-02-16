import glob
import csv
import dateutil
import datetime
import json

# IMPUTATION_PROPERTY_NAME = "http://www.fault-detection.de/hasEstimatedResult" # TODO: Change to new address
IMPUTATION_PROPERTY_NAME = "https://w3id.org/iot/fd/hasEstimatedResult" # TODO: Change to new address
# VERDICT_PROPERTY_NAME = "http://www.fault-detection.de/hasVerdict"
VERDICT_PROPERTY_NAME = "https://w3id.org/iot/fd/hasVerdict"
SIMPLE_RESULT_PROPERTY_NAME = "http://www.w3.org/ns/sosa/hasSimpleResult"

# needed? Monitoring is "controlled" by the MDR, not an API
# class Reply():
#     status = "ok"
#     data = None
#     description = ""
#     success = False
#
#     def __init__(self, status="ok", data=None, description=""):
#         self.status = status
#         self.data = data
#         self.description = description
#         self.success = self.status == "ok"
#
#     def __repr__(self):
#         return json.dumps({"status": self.status, "success": True if self.status == "ok" else False, "description": self.description, "data": self.data})
#
#     def answer(self):
#         return self.__repr__()

class ObservationCache:
    __cache = {}

    @classmethod
    def update(cls, id, value):
        cls.__cache[id] = value

    @classmethod
    def get(cls, id, default=None):
        return cls.__cache[id] if id in cls.__cache else default

def sensorID2CSVFilename(sensorID):
    return sensorID.replace(':', '_')

def loadTrainingData(sensorID, dropSeconds=False):
    """
    We need to use the temporal interface of the broker to look for historic data, which is not working yet.
    As a workaround provide some historic data in CSV files, identifiyable by SensorID.

    input: sensorID = single sensor ID or a list of sensor IDs
            dropSeconds = set the second in the timestamps to 0
    output: {sensorID1: [{"timestamp": XXX, "value": YYY}, ...], sensorID2: [{"timestamp": XXX, "value": YYY}, {}, {}, ...]}
    """
    if not type(sensorID) == list:
        sensorID = [sensorID]
    sensorIDNames = list(map(sensorID2CSVFilename, sensorID))
    result = {}
    for i in range(0, len(sensorIDNames)):
        path = "datasets/*/" + sensorIDNames[i] + ".csv"
        fNames = glob.glob(path, recursive=True)
        # print(fNames)
        if not fNames or len(fNames) == 0:
            continue

        data = []
        for fName in fNames:
            print("reading historic data from:", fName)
            csvFile = csv.DictReader(open(fName, "r"))
            fieldnames = csvFile.fieldnames
            first = True
            for line in csvFile:
                if first:
                    first = False
                    continue
                dt = dateutil.parser.isoparse(line[fieldnames[0]])
                if dropSeconds:
                    dt = dt.replace(second=0)
                # data.append({"timestampStr": dt.isoformat(), "timestamp": dt, "value": float(line[fieldnames[1]])})
                # no timestampStr as agreed in IoTCrawler
                try:
                    data.append({"timestamp": dt, "value": float(line[fieldnames[1]])})
                except:
                    pass # can not log each line that does fail
            # print("loaded", len(data), "samples")
        result[sensorID[i]] = data

    return result

def _makeResultProperty(value, observedAt, isImputed=False):
    valueTemplates = [
        """"value" : %d""", #int
        """"value" : %f""", #float
        """"value" : "%s" """ #string/other
    ]
    vTemplate = 2
    if type(value) == int:
        vTemplate = 0
    if type(value) == float:
        vTemplate = 1

    # template = """"%s" : {
    template = """{"%s" : {
      "type" : "Property",
      """ + valueTemplates[vTemplate] + """,
      "observedAt" : "%s"
    },
    "%s" : {
      "type" : "Property",
      "value": "%s"
    },
    "@context": [
        "http://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
    ] }"""
    # } """

    resultType = IMPUTATION_PROPERTY_NAME #if isImputed else "http://www.w3.org/ns/sosa/hasSimpleResult"
    verdictValue = "faulty" if isImputed else "ok"
    return template % (resultType, value, observedAt, VERDICT_PROPERTY_NAME, verdictValue)

def makeStreamObservation(sensor, value, isImputed=False):

    # import: the stream ID has to be set before using the sensor.setStreamID() method
    # TODO: do we provide both, the original and imputed, values in case auf faulty observation?

    dt = datetime.datetime.now()
    dt = dt.replace(microsecond=0)
    dt_iso = dt.isoformat() + "Z" # the MDR requires the Z at the end
    ngsi_msg = _makeResultProperty(value, dt_iso, isImputed)
    # print(ngsi_msg)
    return json.loads(ngsi_msg)

# def makeFDVerdict(verdict="ok"):
#     template = """{"%s" : {
#       "type" : "Property",
#       "value": "%s"
#     },
#     "@context": [
#         "http://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld"
#     ] }"""
#     # } """
#
#     # resultType = IMPUTATION_PROPERTY_NAME if isImputed else "http://www.w3.org/ns/sosa/hasSimpleResult"
#     return template % (VERDICT_PROPERTY_NAME, verdict)
