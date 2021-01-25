#!/usr/bin/env python

from bottle import get, put, run, request, response, error, HTTP_CODES, hook
import json
import os
import socket
import subprocess

from shutil import copyfile
from subprocess import call
from subprocess import PIPE, Popen
from time import sleep
import time, threading
import datetime
import configparser

def cmdline(command):
    process = Popen(
        args=command,
        stdout=PIPE,
        shell=True
    )
    return process.communicate()[0]

Ssid_Signal = {
    "SSID": "SIGNAL",
    "SSID1": "SIGNA1L"
    }

Ssid_Signal.clear()

API_VERSION = '1.3'
TEST_ADDRESS = ('avnet.iotconnect.io.', 443)
TEST_TIMEOUT = 10

def app_json(func):
    def inner(*args, **kwargs):
        response.content_type = 'application/json'
        # return json.dumps(func(*args, **kwargs), sort_keys=True, indent=4) + '\n'
        return json.dumps(func(*args, **kwargs))
    return inner

@hook('before_request')
def log_requst():
    if request.method == 'PUT':
        print("%s %s: %r" % (request.method, request.path, request.json))
    else:
        print("%s %s:" % (request.method, request.path))

@put('/WiFiClientSSID_PSK')
def wificlient_ssid_psk():
    try:
        rsp = 1
        data = request.body.read()
        data = json.loads(data)
        for key, value in data.items():
            print(key)
            print(value)
            ssid = key
            psk = value
        f = open("/etc/wpa_supplicant/wpa_supplicant.conf","w")
        f.write("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
        f.write("country=US\n")
        f.write("network={\n      key_mgmt=WPA-PSK")
        ssidline = ("\n      ssid=" + "\"" + ssid + "\"\n")
        pskline =  ("\n      psk=" + "\"" + psk + "\"\n")
        f.write(pskline)
        f.write(ssidline)
        f.write("}\n")
        f.close()
        os.system("/bin/bash -c '/opt/avnet-iot/iotservices/wifi_connect &'")
    except Exception as ex:
        print("Exception " + str(ex))
        os.system("ifconfig wlan0 down")
        time.sleep(float(10))
        os.system("ifconfig wlan0 up")
        rsp = 0

    return {'Response' : rsp }

@put('/CloudAttach')
def CloudAttach():
    try:
        rsp = 1
        os.system("/bin/bash -c '/opt/avnet-iot/iotservices/wifi_client &'")
    except:
        rsp = 0

    return {'Response' : rsp }


@put('/IOTNewCPID')
def newcpid():
    print("IOTNEWCPID")
    try:
        config = configparser.ConfigParser()

        config.read('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf')
        rsp = 1
        data = request.body.readline()
        values = json.loads(data)
	config.set('CloudSDKConfiguration','cpid', values['cpid'])
	config.set('CloudSystemControl','username', values['username'])
	config.set('CloudSystemControl','password', values['password'])
	with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf', 'w') as configfile:    # save
            config.write(configfile)
#	with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf.default', 'w') as configfile:    # save
#            config.write(configfile)
        # restart with new settings.
    except:
        rsp = -1

    return {'Response' : rsp }

@put('/WiFiAccessPointDisable')
def wifi_accesspoint_disable():
    try:
        rsp = 1
        # parse ssid/psk and do settings.
	os.system("/bin/bash -c '(sleep 2;/opt/avnet-iot/iotservices/wifi_connect_ignore)&'")
    except:
        rsp = 0
    return {'IsActive' : rsp }

@get('/DeviceId')
def device_id():
    try:
        dev_id = cmdline("/bin/bash -c '/opt/avnet-iot/iotservices/getid'")
        #socket.setdefaulttimeout(10)
        #host = socket.gethostbyname("www.google.com")
        #s = socket.create_connection((host, 80), 2)
        #s.close()
        print(dev_id)
        return {'DeviceId': dev_id}
    except:
        dev_id = '(unknown)'
    return {'DeviceId': dev_id}

@get('/SDKVersion')
def sdk_version():
    try:
        # Fix to use env var
        return {'SDKVersion': API_VERSION}
    except:
        dev_id = '(unknown)'
    return {'DeviceId': dev_id}

@get('/GetSDKLog')
def get_sdk_log():
    try:
        os.system('tail -n 100 /home/avnet/iot.log >/tmp/result.log')
        with open('/tmp/result.log', 'r') as f:
            ret = f.read()
    except:
        ret = "Error"
    return {'GetSDKLog': ret}

@get('/IOTGetIOTConnectSDKConf')
def IOTGetIOTConnectConf():
    try:
        with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf', 'r') as f:
            dev_id = f.read()
    except:
        dev_id = '(unknown)'
    return {'IOTGetIOTConnectSDKConf': dev_id}

@put('/IOTSetIOTConnectSDKConf')
def IOTSetIOTConnectConf():
    ret = 1
    try:
        with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf', 'w') as f:
            data = request.body.read()
            f.write(data)
            f.close()
#        with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf.default', 'w') as f:
#            data = request.body.read()
#            f.write(data)
#            f.close()
    except:
         ret = 0
    return {'IOTSetIOTConnectSDKConf': ret}

@put('/IOTSetAPNConf')
def IOTSetAPNConf():
    ret = 1
    try:
        with open('/etc/apn.conf', 'w') as f:
            data = request.body.read()
            f.write(data)
            f.close()
    except:
         ret = 0
    return {'IOTSetAPNConf': ret}

@get('/IOTGetIOTConnectSDKConfItem')
def IOTGetIOTConnectConfItem():
    ret = 1
    try:
        data = request.body.readline()
        print(data)
        values = json.loads(data)
        for item in values:
            if (item == "SectionName"):
                section_name = values[item]
            if (item == "ValueName"):
		value_name = values[item]

        config = configparser.ConfigParser()
        config.read('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf.default')
        config.read('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf')
        print(config[section_name][value_name])
        ret_dict = {
            "SectionName":"Empty",
        }
	ret_dict["SectionName"] = section_name
        ret_dict[value_name] = config[section_name][value_name]
    	print(ret_dict)
    except Exception as ex:
         print("Exception " + str(ex))
         ret_dict = {
             "SectionName":"Empty",
             "ValueName":"Empty"
         }
         print(ret_dict)
    return {'IOTGetConnectSDKConfItem': ret_dict}

@put('/IOTSetIOTConnectSDKConfItem')
def IOTSetIOTConnectConfItem():
    ret = 1
    try:
        config = configparser.ConfigParser()

        config.read('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf')
        data = request.body.readline()
        values = json.loads(data)
        print(data)
        print(values)
        for item in values:
            print(item)
            print(values[item])
            if (item == "SectionName"):
                section_name = values[item]
            else:
                section_value_name = item
                section_value_data = values[item]
        config.set(section_name, section_value_name, section_value_data)

	with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf', 'w') as configfile:    # save
            config.write(configfile)
#	with open('/opt/avnet-iot/IoTConnect/sample/IoTConnectSDK.conf.default', 'w') as configfile:    # save
#            config.write(configfile)
    except Exception as ex:
         print("Exception " + str(ex))
         ret = 0
    return {'IOTSetConnectSDKConfItem': ret}

@get('/WiFiAccessPointList')
def wifi_list():
    try:
        Ssid_Signal.clear()
        iwlist = cmdline("iwlist wlan0 scan")
        count = 0
        new_cell = False
        have_essid = False
        have_quality = False
        # 'iwlist scan' produces output broken into "Cell"s representing each WiFi AP with details following.
        # Below ensures we match "ESSID" & "Quality" values to one "Cell"
        for item in iwlist.split("\n"):
          if "Cell" in item:
            # New WiFi AP found in list, now must find ESSID and Quality values for it
            new_cell = True
            have_essid = False
            have_quality = False
          if "ESSID" in item:
            essid = item
            essid = essid.split(":")[1]
            essid = essid.replace("\"","")
#            print("ESSID = " + str(essid))
            have_essid = True
          if "Quality" in item:
            quality = item.split("=")[2]
#            print("Quality = " + str(quality))
            have_quality = True
          if new_cell and have_essid and have_quality:
            Ssid_Signal[essid] = quality
            count = count + 1
            new_cell = False
        if (count == 0):
            Ssid_Signal["None Found"] = "-99 dBm"
            s = Ssid_Signal
            print(s)
            return {'WiFiAccessPointList': s}
        s = Ssid_Signal
    except Exception as ex:
        print("Exception" + str(ex))
        s = '(unknown)'
    print(s)
    return {'WiFiAccessPointList': s}


@get('/NetworkStatus')
def network_status():
    connected = False
    try:
        socket.create_connection(TEST_ADDRESS, TEST_TIMEOUT).close()
        connected = True
    except:
        connected = False
    return {'IsConnected': connected}

@get('/WiFiClientConnectionStatus')
def wifi_client_connection_status():
    try:
        f = cmdline("ifconfig wlan0 | grep inet| cut -d 'n' -f2|cut -d 't' -f2")
        if (f == ""):
            addr = '(unknown)'
        else:
            addr = f
    except:
        addr = '(unknown)'
    return {'WiFi client IP':addr}

@get('/WiFiGetIWLIST')
def wifi_get_iwlist():
    try:
	list = cmdline('iwlist wlan0 scan')
    except:
        list = '(unknown)'
    return {'WiFiIWList':list}

@get('/WiFiGetWPAConf')
def wifi_get_wpa():
    try:
	f = open('/etc/wpa_supplicant/wpa_supplicant.conf', 'r')
	conf = f.read()
        print(conf)
    except:
        conf = '(unknown)'
    return {'WiFiWAPConf':conf}

@put('/WiFiSetWPAConf')
def wifi_set_wpa_conf():
    ret = 1
    try:
        data = request.body.read()
	f = open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w')
	f.write(data)
        print(data)
    except:
        ret = 0
    return {'Response':ret}

# TODO: How to decorate for *all* error responses?
# See: https://stackoverflow.com/a/51847982
@error(404)  # Not Found
@error(405)  # Method Not Allowed
@error(500)  # Internal server Error
@app_json
def error_response(error):
    return {
        'Error': response.status_code,
        'Text': HTTP_CODES.get(response.status_code, 'Unknown'),
        'Path': request.path,
        'Method': request.method
    }

if __name__ == '__main__':
    run(host='0.0.0.0', port=8080)
