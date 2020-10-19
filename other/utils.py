import glob
import csv
import dateutil
import datetime

class Reply():
    status = "ok"
    data = None
    description = ""
    success = False

    def __init__(self, status="ok", data=None, description=""):
        self.status = status
        self.data = data
        self.description = description
        self.success = self.status == "ok"

    def __repr__(self):
        return json.dumps({"status": self.status, "success": True if self.status == "ok" else False, "description": self.description, "data": self.data})

    def answer(self):
        return self.__repr__()



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
                data.append({"timestamp": dt, "value": float(line[fieldnames[1]])})
            # print("loaded", len(data), "samples")
        result[sensorID[i]] = data

    return result


def getSensorLocationAndObservableProperty(sensorID):
    """
    Get the location (coordinates) and ObservableProperty ID from a sensor.
    """
    try:
        url = 'http://{}/ngsi-ld/v1/entities/{}'.format(BROKER_ADDRESS, sensorID)
        print("loading:", url)
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            # print("loaded:", response.geturl())
            if response.getcode() != 200: # can this happen? seems urlopen throws an exception if not successful
                print("Error:", response.getcode())
                return Reply("error")
            else:
                data = response.read()
                d = json.loads(data)
                sensor = Sensor(d)
                return Reply(data={'location': sensor.location(), "propertyID": sensor.observesPropertyID()})

    except urllib.error.HTTPError as e:
        print(e)
        msg = str(e.read())
        return Reply("error", description="Could not load ObservableProperties: " + str(e) + msg)


# needed? in VS Creator used to find neighbours
# def getObservablePropertyLabel(propertyID):
#     """
#     Get the label for an ObservableProperty.
#     """
#     try:
#         req = urllib.request.Request('http://{}/ngsi-ld/v1/entities/{}'.format(BROKER_ADDRESS, propertyID), headers={"Accept": "application/json"})
#         with urllib.request.urlopen(req, timeout=10) as response:
#             # print("loaded:", response.geturl())
#             if response.getcode() != 200: # can this happen? seems urlopen throws an exception if not successful
#                 print("Error:", response.getcode())
#                 return Reply("error")
#             else:
#                 data = response.read()
#                 d = json.loads(data)
#                 if not "http://www.w3.org/2000/01/rdf-schema#label" in d:
#                     return Reply("error")
#                 label = d["http://www.w3.org/2000/01/rdf-schema#label"]
#                 if not "value" in label:
#                     return Reply("error")
#                 label = label["value"]
#                 return Reply(data={'label': label, "propertyID": propertyID})
#
#     except urllib.error.HTTPError as e:
#         print(e)
#         msg = str(e.read())
#         return Reply("error", description="Could not load ObservableProperties: " + str(e) + msg)

def getSteamID(sensorID):
    """
    Get the IoT-Stream ID belonging to a sensor identified by sensorID
    """
    try:
        req = urllib.request.Request('http://{}/ngsi-ld/v1/entities/?type=http://purl.org/iot/ontology/iot-stream%23IotStream&q=http://purl.org/iot/ontology/iot-stream%23generatedBy=={}'.format(BROKER_ADDRESS, sensorID), headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as response:
            # print("loaded:", response.geturl())
            if response.getcode() != 200: # can this happen? seems urlopen throws an exception if not successful
                print("Error:", response.getcode())
                return Reply("error")
            else:
                # print("getStreamID URL:", req.full_url)
                data = response.read()
                d = json.loads(data)
                if len(d) == 0 or not "id" in d[0]:
                    return Reply("error", description="ID for stream belonging to sensor not found")
                return Reply(data={'streamID': d[0]["id"], "sensorID": sensorID})

    except urllib.error.HTTPError as e:
        print(e)
        msg = str(e.read())
        return Reply("error", description="Could not load Stream ID: " + str(e) + msg)

def makeStreamObservation(sensor, value):
    sensorID = sensor.ID()
    # if not sensor.getSteamID():
    #     sID = getStreamID(sensorID)
    #     if sID.success:
    #         sensor.setStreamID(sID.data[streamID])

    dt = datetime.datetime.now()
    dt = dt.replace(microsecond=0)
    dt_iso = dt.isoformat() + "Z" # the MDR requires the Z at the end
    ngsi_msg = """{
  "id" : "%s",
  "type" : "http://purl.org/iot/ontology/iot-stream#StreamObservation",
  "http://purl.org/iot/ontology/iot-stream#belongsTo" : {
    "type" : "Relationship",
    "object" : "%s"
  },
  "http://www.w3.org/ns/sosa/hasSimpleResult" : {
    "type" : "Property",
    "value" : %f,
    "observedAt" : "%s"
  },
  "http://www.w3.org/ns/sosa/madeBySensor" : {
    "type" : "Relationship",
    "object" : "%s"
  },
  "http://www.w3.org/ns/sosa/observedProperty" : {
    "type" : "Relationship",
    "object" : "%s"
  },
  "http://www.w3.org/ns/sosa/resultTime" : {
    "type" : "Property",
    "value" : "%s"
  },
  "@context" : [ "https://uri.etsi.org/ngsi-ld/v1/ngsi-ld-core-context.jsonld" ]
}
    """ % (sensor.streamObservationID(), sensor.getStreamID(), value, dt_iso, sensor.ID(), sensor.observesPropertyID(), dt_iso)
    # TODO: send to broker
    # brokerHelper.create_ngsi_entity(json.loads(ngsi_msg))
    return json.loads(ngsi_msg)
