import csv
import datetime
sensor_ids = [13003, 13004, 13005, 13006]
fieldNames = ["timestamp","humidity","air_temperature","barometric_pressure","battery","eCO2","TVOC","light","PM_1","noise","PM_10","PM_2.5"]
fieldNamesMap = {"humidity":"humidity in % (SHT31 - Humidity)","air_temperature":"air temperature in ºC (SHT31 - Temperature)","barometric_pressure":"barometric pressure in K Pa (MPL3115A2 - Barometric Pressure)","battery":"battery in % (Battery SCK 1.1)","eCO2":"eCO2 in ppm (AMS CCS811 - eCO2)","TVOC":"TVOC in ppb (AMS CCS811 - TVOC)","light":"light in Lux (BH1730FVC)","PM_1":"PM 1 in ug/m3 (PMS5003_AVG-PM1)","noise":"noise in dBA (ICS43432 - Noise)","PM_10":"PM 10 in ug/m3 (PMS5003_AVG-PM10)","PM_2.5":"PM 2.5 in ug/m3 (PMS5003_AVG-PM2.5)"}
sensorNameTemplate = "urn_ngsi-ld_Sensor_SmartCitizen_{}_{}.csv"
writers = {}

if __name__ == '__main__':
    for sensorID in sensor_ids:
        print("handling sensor", sensorID)
        csvFile = open(str(sensorID) + ".csv", "r")
        reader = csv.DictReader(csvFile)

        for fieldname in fieldNames:
            if fieldname == "timestamp":
                continue
            sensorname = sensorNameTemplate.format(sensorID, fieldname)
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
