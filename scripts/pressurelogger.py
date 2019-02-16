import serial
import time
import datetime
from influxdb import InfluxDBClient
from ConfigParser import SafeConfigParser 

# Failure recovery libraries
import json
import os
import time
import errno

ser = serial.Serial()

#Load settings in the config file
parser = SafeConfigParser({'location':'/dev/shm/missedPressureLogs'})
parser.read('/etc/pressurelogger/pressurelogger.conf')	
serialport = parser.get('serial','port')
serialbaudrate = parser.get('serial','baudrate')
	
# Configure settings for the XGS-600, see page 75 of the user manual for the default settings
ser.port = serialport
ser.baudrate = serialbaudrate # Bits per second, either 9600 (the default) or 19200, depending on what is set on XGS-600
ser.bytesize = serial.EIGHTBITS # Number of data bits
ser.parity = serial.PARITY_NONE # Enable parity checking
ser.stopbits = serial.STOPBITS_ONE #Number of stop bits
ser.xonxoff = False #Software flow control     
ser.rtscts = False # Hardware flow control (RTS/CTS)   
ser.dsrdtr = False  # Hardware flow control (DSR/DTR)
		

try:
	ser.open()
except Exception as e:
	print ("Error opening serial port:")
	print e
	exit()

if ser.isOpen():

	try:
		ser.flushInput()
		ser.flushOutput() 
		ser.timeout = 1 # Returns 1 second after reading

		# Sends serial command
		ser.write("#000F\r")
		print("Serial command sent")

   		# Reads serial command
		pressure = ser.readline() # This will not work if you not specify the timeout value
		print ("Current pressure: " + pressure)
		
		# Splits the string and assigns it to three separate variables
		main, tc, oven = pressure.split(",") 
		main = main[1:] # Removes the first char

		# Converts from string to float
		main = float(main)
		tc = float(tc)
		oven = float(oven)
		
		# Stores values in an array 
		try:
			current_time = str(datetime.datetime.utcnow())
			print ("Main chamber pressure {0} Transverse cooling pressure {1} Oven pressure {2}".format(main, tc, oven)) 
			data_body = [
				{
					"measurement": "pressure",
					"time": current_time,
					"fields": {
						"main chamber": main,
						"transverse cooling": tc,
						"oven": oven
					}
				}
			]		
		except Exception as e2:
			print ("Error storing data:")
			print (e2)
			
		# Sends data to InfluxDB server 
		try:
			influx_url = parser.get('influx', 'url')
			influx_port = parser.get('influx', 'port')
			influx_user = parser.get('influx', 'username')
			influx_pwd = parser.get('influx', 'password')
			influx_db = parser.get('influx', 'database')
			client = InfluxDBClient(influx_url, influx_port, influx_user, influx_pwd, influx_db)
			client.write_points(data_body)
			
		# Data recovery code was adapted from: https://github.com/JQIamo/RPi-Temp-Humidity-Monitor	
		# Data is saved locally on failure	
		except Exception as e3:
			print ("Error sending data:")
			print (e3)
			missedDirectory = parser.get('missed','location')
			try:
				os.makedirs(missedDirectory)
			except OSError as exception:
				if exception.errno != errno.EEXIST:
					raise
			saveFilename = "%d-missedPressure.json" % time.time()
			savePath = os.path.join(missedDirectory, saveFilename)
			print ("Attempting to save pressure readings locally to %s" % savePath)
			with open(savePath,'w') as outfile:
				json.dump(data_body, outfile)						
		ser.close()
	except Exception as e1:
		print ("Error communication failed:" )
		print(e1)
else:
	print ("Serial port cannot be opened")
