import csv
import datetime
import zipfile
import json
import sys

fieldNames = ["temperature", "CO", "illuminance", "pressure", "battery", "humidity", "NO2", "PM10", "PM2.5"]
jsonEncodedFieldNames = ["noise", "rain"]
jsonKeys = ["min", "max", "average"]
sensorNameTemplate = "urn_ngsi-ld_Sensor_Cityprobe_{}_{}.csv"
writers = {}

if __name__ == '__main__':
    # get all sensor/device ids
    print("collecting all sensor IDs")
    sensor_ids = []

    #this did not work correctly as the are deviceids in the data not listed here
    # csvFile = open("device-locations.csv", "r")
    # reader = csv.DictReader(csvFile, delimiter=";")
    # for row in reader:
    #     sensor_ids.append(row['deviceid'])

    zipFile = zipfile.ZipFile("data.zip")

    csvFile = zipFile.open("data.csv", "r")
    csvContent = []
    for line in csvFile:
        csvContent.append(str(line))
    zipFile.close()

    reader = csv.DictReader(csvContent, delimiter=",")
    for row in reader:
        sensor_ids.append(row['deviceid'])
    #remove duplicates
    sensor_ids = list(dict.fromkeys(sensor_ids))

    print("Found", len(sensor_ids), "sensors")

    #create a writer for each sensor and each field
    print("preparing files ... ", end='', flush=True)
    writerFiles = []
    try:
        for sensorID in sensor_ids:
            for fieldname in fieldNames:
                sensorname = sensorNameTemplate.format(sensorID, fieldname)
                key = sensorID+fieldname
                writerFile = open(sensorname, "w")
                writers[key] = csv.DictWriter(writerFile, fieldnames=["timestamp", "value"])
                writers[key].writeheader()
                writerFiles.append(writerFile)
            for fieldname in jsonEncodedFieldNames:
                for jk in jsonKeys:
                    fn = fieldname + "_" + jk
                    sensorname = sensorNameTemplate.format(sensorID, fn)
                    key = sensorID+fn
                    writerFile = open(sensorname, "w")
                    writers[key] = csv.DictWriter(writerFile, fieldnames=["timestamp", "value"])
                    writers[key].writeheader()
                    writerFiles.append(writerFile)
    except OSError as e:
        print(e)
        print("If the error says to many open files run 'ulimit -n 1024' to increase the limit.")
        sys.exit(1)
    print("done")

    #iterate over the data file and for each field write the data to the corresponding writer
    print("Sorting data ... ", end='', flush=True)
    reader = csv.DictReader(csvContent, delimiter=",")
    for row in reader:
        tsStr = row['published_at'][:-1]
        ts = datetime.datetime.fromisoformat(tsStr)
        ts = ts.replace(microsecond=0)
        for fieldname in fieldNames:
            key = row['deviceid']+fieldname
            data = {"timestamp": ts.isoformat(), "value": row[fieldname]}
            writers[key].writerow(data)
        for fieldname in jsonEncodedFieldNames:
            d = json.loads(row[fieldname])
            for jk in jsonKeys:
                fn = fieldname + "_" + jk
                key = row['deviceid']+fn
                data = {"timestamp": ts.isoformat(), "value": d[jk]}
                writers[key].writerow(data)

    print("finished")
    #close all writers
    for w in writerFiles:
        w.close()
