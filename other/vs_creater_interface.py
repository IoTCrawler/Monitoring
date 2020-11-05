from configuration import Config
import requests
import logging


def replaceBrokenSensor(sensorID, maxDistance=20000, onlySameObservations=True, limitSourceSensors=8, updateInterval=60):
    payload = {
      "sensorID" : sensorID,
      "maxDistance": maxDistance,
      "onlySameObservations": onlySameObservations,
      "limitSourceSensors": limitSourceSensors,
      "updateInterval": updateInterval
    }
    server_url = Config.getEnvironmentVariable('VS_CREATER_ADDRESS') + "/api/replaceBrokenSensor/"
    r = requests.get(server_url, json=payload)
    if r.status_code == 200:
        reply = r.json()
        return reply["success"]

def stopVirtualSensor(sensorID):
    payload = {
      "sensorID" : sensorID
    }
    server_url = Config.getEnvironmentVariable('VS_CREATER_ADDRESS') + "/api/stopVirtualSensor/"
    r = requests.get(server_url, json=payload)
    if r.status_code == 200:
        reply = r.json()
        return reply["success"]
