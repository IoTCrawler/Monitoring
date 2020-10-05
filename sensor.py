import json
from time import sleep



class Sensor:
    ngsild = None
    lastValue = 0
    streamID = None

    def __init__(self, ngsildCode):
        if type(ngsildCode) == str:
            self.ngsild = json.loads(ngsildCode)
        else:
            self.ngsild = ngsildCode
        self.trainingData = None

    def __saveGet(self, *args):
        obj = self.ngsild
        for key in args:
            if not key in obj:
                return None
            obj = obj[key]
        return obj

    def coordinates(self):
        """
        returns a tuple (latitude, longitude)
        """
        latlong = self.__saveGet("location", "value", "coordinates")
        return (latlong[0], latlong[1])

    def location(self):
        """
        returns a list [latitude, longitude]
        """
        return self.__saveGet("location", "value", "coordinates")

    def observesPropertyID(self):
        return self.__saveGet("http://www.w3.org/ns/sosa/observes", "object")

    def ID(self):
        return self.__saveGet("id")

    def getStreamID(self):
        return self.streamID

    def setStreamID(self, streamID):
        self.streamID = streamID

    def platformID(self):
        return self.__saveGet("http://www.w3.org/ns/sosa/isHostedBy", "object")

    def streamObservationID(self):
        return self.__saveGet("http://www.w3.org/ns/sosa/madeObservation", "object")

    def subscriptionID(self):
        return self.ID() + ":Subscription"

    def updateInterval(self):
        ui = self.__saveGet("https://w3id.org/iot/qoi#updateinterval", "value")
        if not ui:
            return -1
        unit = self.__saveGet("https://w3id.org/iot/qoi#updateinterval", "https://w3id.org/iot/qoi#unit", "value")
        if not unit or unit in ("NA", "seconds", "second", "s"):
            return ui
        if unit in ("minutes", "minute", "m"):
            return ui * 60
        if unit in ("hours", "hour", "h"):
            return ui * 3600

    def trainingData():
        doc = "The trainingData property."
        def fget(self):
            return self._trainingData
        def fset(self, value):
            self._trainingData = value
        def fdel(self):
            del self._trainingData
        return locals()
    trainingData = property(**trainingData())


# Still needed?
class VirtualSensor(Sensor):
    thread = None
    updateInterval = 300 # 5 Minutes
    counter = 0
    stopRunning = False
    model = None
    contributingSensors = {}
    orderedContributingSensorIDs = []
    replacedSensorID = ""
    alignedTrainingData = None
    predictionCallback = None

    # related entities
    platform = None
    stream = None
    observation = None
    qoi = None

    def __init__(self, ngsildCode, contributingSensors, updateInterval=300, replacedSensorID="", alignedTrainingData=None, predictionCallback=None):
        Sensor.__init__(self, ngsildCode)
        self.updateInterval = updateInterval
        self.contributingSensors = contributingSensors
        self.replacedSensorID = replacedSensorID
        self.alignedTrainingData = alignedTrainingData # don't mix up with trainingData by Sensor super class
        self.predictionCallback = predictionCallback

        for cs in self.contributingSensors:
            self.orderedContributingSensorIDs.append(cs)
        self.orderedContributingSensorIDs.sort()



    # def stop(self):
    #     self.stopRunning = True
    #
    # def train(self, onCompletion=None):
    #     if not self.alignedTrainingData:
    #         print("No training data. Unable to learn.")
    #         return
    #
    #     # TODO: use previously trained model?
    #     # modelfile = 'models/model.sav'
    #     # model = learner(df, corr_ids)
    #     # pickle.dump(model, open(modelfile, 'wb'))
    #     # model = pickle.load(open(modelfile, 'rb'))
    #
    #     print(self.ID(), "training")
    #     df, corr_ids = self.alignedTrainingData
    #     self.model = learner(df, corr_ids)
    #     # self.model = FakeModel()
    #     print(self.ID(), "model created")
    #     if onCompletion:
    #         onCompletion(self)
    #     self.execute()

    # def execute(self):
    #     while not self.stopRunning:
    #         self.counter += 1
    #         if self.counter == self.updateInterval:
    #             self.counter = 0
    #             try:
    #                 self.predict()
    #             except:
    #                 print("Error during predication at sensor", self.ID())
    #         sleep(1.0)
    #     print(self.ID(), "stopped")

    def updateValue(self, sensorID, value):
        """
        Update the value of a contributing sensor
        """
        for cs in self.contributingSensors:
            if self.contributingSensors[cs].ID() == sensorID:
                self.contributingSensors[cs].lastValue = value
                print("updated last value for", sensorID, "to", value, "as", cs)

    # def predict(self):
    #     # TODO get all current reading from the contributing sensors
    #     values = []
    #     for csID in self.orderedContributingSensorIDs:
    #         if csID in self.contributingSensors:
    #             values.append(self.contributingSensors[csID].lastValue)
    #
    #     # prediction = self.model.predict(1, 2, 3)
    #     prediction = self.model.predict([values])
    #     if self.predictionCallback:
    #         self.predictionCallback(self, prediction)
