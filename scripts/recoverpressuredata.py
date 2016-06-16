from influxdb import InfluxDBClient
from ConfigParser import SafeConfigParser 

# Failure recovery libraries
import json
import os
import time
import errno

parser = SafeConfigParser({'location':'/dev/shm/missedPressureLogs'})
parser.read('/etc/pressurelogger/pressurelogger.conf')

# Data recovery code was adapted from: https://github.com/JQIamo/RPi-Temp-Humidity-Monitor
# Recovers data stored locally
data_body=[]
try:
	missedDirectory = parser.get('missed','location')
	for file in os.listdir(missedDirectory):
		if file.endswith('-missedPressure.json'):
			fullPath = os.path.join(missedDirectory, file)
			with open(fullPath, 'r') as recoverfile:
				recoverdata=json.load(recoverfile)
			data_body += recoverdata
			os.remove(fullPath)
except Exception as e:
	print "Error recovering local data:"
	print e

# Resends data to the server
try:
	influx_url = parser.get('influx', 'url')
	influx_port = parser.get('influx', 'port')
	influx_user = parser.get('influx', 'username')
	influx_pwd = parser.get('influx', 'password')
	influx_db = parser.get('influx', 'database')
	client = InfluxDBClient(influx_url, influx_port, influx_user, influx_pwd, influx_db)
	client.write_points(data_body)
	
# The data is saved locally on failure	
except Exception as e1:
	print e1
	print "Attempting to save pressure readings locally to %s" % savePath
	try:
		os.makedirs(missedDirectory)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise
	saveFilename = "%d-missedPressure.json" % time.time()
	savePath = os.path.join(missedDirectory, saveFilename)
	with open(savePath,'w') as outfile:
		json.dump(data, outfile)						


