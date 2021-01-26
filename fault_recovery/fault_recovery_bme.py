import logging

from oct2py import octave
import pprint
import numpy as np
import pandas as pd
import os.path
from ngsi_ld.broker_interface import find_neighbor_sensors, get_observable_property_label
import subprocess
from sensor import Sensor
from other.utils import loadTrainingData, ObservationCache
from copy import deepcopy

logger = logging.getLogger('monitoring')

class FaultRecoveryBME:

    def __init__(self):
        # octave.addpath('/home/aurorax/Git_repos/postdoc/JoseMendoza/20200807current_missing_values/IoTcrawler/BMEImputation/')
        octave_path =  os.path.join(os.path.dirname(os.path.abspath(__file__)), "BME_implementation", "BMEImputation")
        octave.addpath(octave_path)

        self.r_script_path =  os.path.join(os.path.dirname(os.path.abspath(__file__)), "BME_implementation", "vario", "script1.R")
        self.sensor = None
        self.neighbours = None
        self.varparam = None
        self.varmodel = 'gaussianC'   #modelo de variograma
        self.locations_array = None
        self.trainedSensors = [] # keep track of sensors we have finished training

    def newSensor(self, sensorID, entity):
        print("FR BME newSensor called")
        self.sensor = Sensor(entity)
        if not self.neighbours:
            self.neighbours = []
            # TODO: search for neighbours, prepare 'datos' and 'localizaciones'
            lat, lng = self.sensor.coordinates()
            radius = 2000 # may depend on the use case/scenario
            label = get_observable_property_label(self.sensor.observesPropertyID())
            sensors = find_neighbor_sensors(self.sensor.ID(), label, lat, lng, radius)
            if len(sensors) == 0:
                print("no neighbours found")
                return
            # print(sensors)
            trainingIDs = [sensorID] # IDs for which we need training data
            for s in sensors:
                sensor = Sensor(s)
                self.neighbours.append(sensor)
                trainingIDs.append(sensor.ID())

            trainingDataAll = loadTrainingData(trainingIDs)
            if len(trainingDataAll) == 0:
                # no training data found :(
                return

            if not sensorID in trainingDataAll:
                # we got some training data, but not for the faulty one
                return

            # datos = pd.read_csv('dataparking.csv', sep=' ', header=None)
            # datosS = datos.to_string()

            # find which training dataset has the fewest samples
            shortest = 100
            for id in trainingDataAll:
                shortest = min(shortest, len(trainingDataAll[id]))

            # header line (just column indices)
            lines = [ " ".join(list(map(str, range(shortest)))) ] # '0  1  2  3 .... shortest-1'
            # extract all values of the 'shortest' newest samples and convert them to strings
            values = list(map(lambda x: str(x['value']), trainingDataAll[sensorID][-shortest:]))
            lines.append("0 %s" % (" ".join(values),) )

            i = 0
            rm_idx = []
            for x in range(len(self.neighbours)):
                n = self.neighbours[x]
                if n.ID() == sensorID:
                    continue
                if not n.ID() in trainingDataAll:
                    rm_idx.append(x)
                    continue
                i += 1
                values = list(map(lambda x: str(x['value']), trainingDataAll[n.ID()][-shortest:]))
                lines.append("%d %s" % (i, " ".join(values)) )
            datosS = "\n".join(lines)

            # remove all sensor from the neighbours list for which no training data was found
            rm_idx = sorted(rm_idx, reverse=True)
            for x in rm_idx:
                del self.neighbours[x]

            # localizaciones = pd.read_csv('locationsparking.txt', sep='\t', header=None)
            # localizacionesS = localizaciones.to_string()
            # '   0          1         2\n0  1  37.989825 -1.132959\n1  2  37.992907 -1.133843\n2  3  37.994971 -1.129519'
            lines = [ "0 1 2"]
            lat, lng = self.sensor.coordinates()
            lines.append("0 1 %f %f" % (lat, lng))
            for i in range(0, len(self.neighbours)):
                if not self.neighbours[i].ID() in trainingDataAll:
                    # no training data for this neighbour, skip
                    continue
                lat, lng = self.neighbours[i].coordinates()
                lines.append("%d %d %f %f" % ((i+1), (i+2), lat, lng))
            localizacionesS = "\n".join(lines)

            #
            modelo = 'gausiano' #""pepita", "esferico", "exponencial", "gausiano"
            result = subprocess.check_output(['Rscript', self.r_script_path, datosS, localizacionesS, modelo], universal_newlines = True)
            parts = result.split(sep=" ")
            sill = float(parts[0])
            rang = float(parts[1])
            nugget = float(parts[2])
            # varparam = [[901.716912014706],[0.000115966796875], [0]]   #previously computed var and sill variogram values
            self.varparam = [[sill],[rang], [nugget]]   #previously computed var and sill variogram values
            print(self.varparam)
            self.trainedSensors.append(sensorID)
            logger.debug("FR BMC: training of " + sensorID + " finished")

    def update(self, sensorID, value):
        if not sensorID in self.trainedSensors or len(self.neighbours) == 0:
            # training not finished or no neighbours found, nothing we can do
            logger.error("FR BMC: update called for untrained sensor " + sensorID)
            return None
        print("FR BME update called")
        data = [ObservationCache.get(n.ID(), 0.0) for n in self.neighbours] # [263.0, 217.0] #known values from valid sensors
        id = 1
        ids = list(range(2, len(self.neighbours)+2)) #[2,3] #

        if not self.locations_array:
            # locations = [[37.989825, -1.132959],[37.992907, -1.133843],[37.994971, -1.129519]]
            lat, lng = self.sensor.coordinates()
            self.locations_array = [[lat,lng]]
            for n in self.neighbours:
                lat, lng = n.coordinates()
                self.locations_array.append([lat, lng])

        prediction = octave.hardBME(id, ids, data, self.locations_array, self.varmodel, self.varparam)
        print("BME prediction:", prediction)
        return prediction
