import csv
import datetime
import requests

sensor_ids = [13003, 13004, 13005, 13006]
fieldNames = ["timestamp","humidity","temperature","barometric_pressure","battery","eCO2","TVOC","light","PM_1","noise","PM_10","PM_2.5"]
fieldNamesMap = {"humidity":"humidity in % (SHT31 - Humidity)","temperature":"air temperature in ºC (SHT31 - Temperature)","barometric_pressure":"barometric pressure in K Pa (MPL3115A2 - Barometric Pressure)","battery":"battery in % (Battery SCK)","eCO2":"eCO2 in ppm (AMS CCS811 - eCO2)","TVOC":"TVOC in ppb (AMS CCS811 - TVOC)","light":"light in Lux (BH1730FVC)","PM_1":"PM 1 in ug/m3 (PMS5003_AVG-PM1)","noise":"noise in dBA (ICS43432 - Noise)","PM_10":"PM 10 in ug/m3 (PMS5003_AVG-PM10)","PM_2.5":"PM 2.5 in ug/m3 (PMS5003_AVG-PM2.5)"}
sensorNameMap = {13003: "10adb27d-123e-4ca8-8a59-7ab215a180f5", 13004: "5a94c24c-12f1-48a1-8a42-9b31011bec1b", 13005: "a7ba136d-9a06-432b-9ec4-175a018bfd5", 13006: "f0cf1a0b-5d7c-4501-acad-f768a9dba3c5"}
# sensorNameTemplate = "urn_ngsi-ld_Aarhus_Staging_{}_{}_{}.csv"
sensorNameTemplate = "urn_ngsi-ld_Sensor_Aarhus_Staging_{}_{}.csv"
writers = {}

if __name__ == '__main__':
    for sensorID in sensor_ids:
        print("handling sensor", sensorID)
        csvFile = open(str(sensorID) + ".csv", "r")
        reader = csv.DictReader(csvFile)

        if not sensorID in sensorNameMap:
            print("No mapping for sensor id", sensorID)
            continue

        aarhusID = sensorNameMap[sensorID]
        url = "https://iot-crawler-adapter.srvitkiot01.itkdev.dk/devices/" + aarhusID
        r = requests.get(url)
        if r.status_code != 200:
            print("Loading device information for", sensorID, "returned:", r.status_code)
            continue
        data = r.json()

        sID = "unknown"

        for fieldname in fieldNames:
            if fieldname == "timestamp":
                continue
            for sensor in data['sensors']:
                if sensor['name'] in fieldNamesMap[fieldname]:
                    sID = sensor['id']
                    break
            # sensorname = sensorNameTemplate.format(aarhusID, sID, fieldname)
            sensorname = sensorNameTemplate.format(aarhusID, sID)
            writerFile = open(sensorname, "w")
            writers[fieldname] = csv.DictWriter(writerFile, fieldnames=["timestamp", "value"])
            writers[fieldname].writeheader()

        for row in reader:
            ts = datetime.datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S UTC")
            for fieldname in fieldNames:
                if fieldname == "timestamp":
                    continue
                data = {"timestamp": ts.isoformat(), "value": row[fieldNamesMap[fieldname]]}
                writers[fieldname].writerow(data)
    print("finished")
