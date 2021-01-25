import traceback
import sys
import os.path
import os
import httplib
from os import environ
from iotconnect import IoTConnectSDK
import json
import time
import socket
import configparser
import minimalmodbus
import usbinfo
import wget
import Smart_Sensor
import ctypes
import threading
import psutil
global OmegaZWLock
global OmegaSSLock
global MessageCount
#from gc import mem
#mem.enable()
MessageCount = 0
IoTConnectConnecting = 1

global SendDataLock
global PushDataNow
PushDataNow = 0
global PushDataArray
PushDataArray = []

OmegaZWLock = threading.Lock()
OmegaSSLock = threading.Lock()
SendDataLock = threading.Lock()

import re
import subprocess
from subprocess import PIPE, Popen
global ThreadCount
ThreadCount = 0
global OmegaServer
import ZW_REC_Interface


def cmdline(command):
    try:
        process = Popen(
                args=command,
                stdout=PIPE,
                shell=True
        )
        return process.communicate()[0]
    except:
        print(ex)
    return None

template_name = 0
isedge = 0
isgateway = 0
global SendDataArray
SendDataArray = []

from datetime import datetime

from urlparse import urlparse

AUTH_BASEURL = ""
TEMPLATE_BASEURL= ""
DEVICE_BASEURL= ""

ACCESS_TOKEN = None
global uniqueId
global EndorsementKey
global serial_number
serial_number = 0
EndorsementKey = "1"
uniqueId = 0
template = None
templateDescription = 0
deviceTemplateGuid = None
cpId = None
ActiveIP = {}
my_config_parser_dict = {}
from collections import defaultdict
my_sensor_dict = defaultdict(dict)
my_rules_dict = defaultdict(dict)
my_command_dict = {}
Aquired_Usb = defaultdict(dict)
sdk = 0
import pyudev

while not os.path.exists("/sys/class/leds/green/brightness"):
    time.sleep(2)
    myprint("Waiting for green led")
os.system('chmod 666 /sys/class/leds/green/brightness')
os.system('echo 0 >/sys/class/leds/green/brightness')

while not os.path.exists("/sys/class/leds/red/brightness"):
    time.sleep(2)
    myprint("Waiting for green red")
os.system('chmod 666 /sys/class/leds/red/brightness')
os.system('echo 0 >/sys/class/leds/red/brightness')

def ctype_async_raise(thread_obj, exception):
    found = False
    target_tid = 0
    for tid, tobj in threading._active.items():
        if tobj is thread_obj:
            found = True
            target_tid = tid
            break

    if not found:
        return

    ret = ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, ctypes.py_object(exception))
    # ref: http://docs.python.org/c-api/init.html#PyThreadState_SetAsyncExc
    if ret == 0:
        raise ValueError("Invalid thread ID")
    elif ret > 1:
        # Huh? Why would we notify more than one threads?
        # Because we punch a hole into C level interpreter.
        # So it is better to clean up the mess.
        ctypes.pythonapi.PyThreadState_SetAsyncExc(target_tid, NULL)
        raise SystemError("PyThreadState_SetAsyncExc failed")
    #print "Successfully set asynchronized exception for", target_tid)


def service_call(method, url, header=None, body=None):
    try:
        data = None
        parsed_uri = urlparse(url)
        scheme = parsed_uri.scheme
        host = parsed_uri.hostname
        port = parsed_uri.port
        path = parsed_uri.path

        if parsed_uri.query:
            path = '%s?%s' % (path, parsed_uri.query)

        if port == None:
            if scheme == "http":
                conn = httplib.HTTPConnection(host)
            else:
                conn = httplib.HTTPSConnection(host)
        else:
            if scheme == "http":
                conn = httplib.HTTPConnection(host, port)
            else:
                conn = httplib.HTTPSConnection(host, port)

        if body == None:
            if header != None:
                conn.request(method, path, headers=header)
            else:
                conn.request(method, path)

        if body != None:
            body = json.dumps(body)
            if header != None:
                conn.request(method, path, body, headers=header)
            else:
                conn.request(method, path, body)

        response = conn.getresponse()
        if response.status == 200:
            data = response.read()
            data = json.loads(data.decode('utf-8'))
        else:
            myprint("Bad http response: " + str(response.status))
            myprint("  " + str(method) + " " + str(url) + " " + str(header) + " " + str(body))
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        print(ex)
        sys.stdout.flush()
        sys.stderr.flush()
        myprint("No network")
    finally:
        conn.close()
        return data

def get_auth(username, password, solution_key):
    try:
        access_token = None
        data = None
        authToken = service_call("GET", AUTH_BASEURL + "/auth/basic-token")
        if authToken != None:
            data = str(authToken["data"])
        if data != None:
            body = {}
            body["username"] = username
            body["password"] = password
            header = {
                    "Content-type": "application/json",
                    "Accept": "*/*",
                    "Authorization": 'Basic %s' % data,
                    "Solution-key": solution_key
            }
            data = service_call("POST", AUTH_BASEURL + "/auth/login", header, body)
            if data != None:
                access_token = str('Bearer %s' % data["access_token"])
        return access_token
    except:
        return None


def DoCommand(msg):
    global my_command_dict
    global my_sensor_dict
    myprint("Executing command")
    command = str(msg['data']['command'])
    data = command.split()
    if (data[0] == 'OmegaCommand'):
        myprint("Omega Cmd")
        output = data[1]
        for item in my_sensor_dict:
            if (str(item) == str(output)):
                myprint("\nFound Omega Output item")
                mydev = my_sensor_dict[item]['OmegaDev']
                mydev.Output_Data(int(my_sensor_dict[item]['OmegaSensorNumber']) - 1, int(data[2]), my_sensor_dict[item]['OmegaSSDevice'])
                myprint("\nOmega Command executed on output " + str(item))
    else:
        myprint("Python command")
        globals()[my_command_dict[command.strip()]](msg)
        myprint("Command Executed")
    for item in my_config_parser_dict:
        if 'name' in my_config_parser_dict[item].keys():
            if (my_config_parser_dict[item]['name'] == str(command)):
                if (int(my_config_parser_dict[item]['requiresack']) == 1):
                    sendack = 1
                else:
                    sendack = 0
    if (sendack == 1):
        header = {
            "ackId":msg['data']['ackId'],
            "st":7,
            "msg":"OK"
        }
        sdk.SendACK(header,5)


def myprint(arg):
    try:
        print(arg)
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass

def DoOTACommand(msg):
    myprint(str(msg['data']['command']))
    mystring=str(msg['data']['command'])
    if [ mystring.split(" ")[0] == "ota" ]:
        filename = wget.download(msg['data']['urls'][0]['url'])
        cmd = "mv " + filename + " install.gz "      
        os.system(cmd)
        cmd = "gunzip -c install.gz >install"
        os.system(cmd)
        cmd = "tar xf install"
        os.system(cmd)
        os.system("chmod 777 updates/install.sh")
        os.system("./updates/install.sh")
        header = {
            "ackId":msg['data']['ackId'],
            "st":7,
            "msg":"OK"
        } 
        sdk.SendACK(header,11)



def callbackMessageThread(msg):
    global sdk, my_command_dict
    myprint(msg)
    myprint(str(msg['data']['ack']))
    myprint(str(msg['data']['ackId']))
    myprint(str(msg['data']['command']))
    myprint(str(msg['data']['uniqueId']))
    if msg != None and len(list(msg.items())) != 0:
        cmdType = msg["cmdType"]
        data = msg["data"]
        # For Commands
        if cmdType == "0x01" and data != None:
            DoCommand(msg)
        # For OTA updates
        if cmdType == "0x02" and data != None:
            DoOTACommand(msg)
      # if not OTA then everything else send to user_callbackMessage
        if cmdType != "0x02":
            globals()['user_callbackMessage'](msg)

def callbackMessage(msg):
    x = threading.Thread(target=callbackMessageThread, args=(msg,))
    x.daemon = True
    x.start()
        

def get_template(searchText):
    global ACCESS_TOKEN
    try:
        header = {
                "Content-type": "application/json",
                "Accept": "*/*",
                "Authorization": ACCESS_TOKEN
        }

        templates = []
        response = service_call("GET", TEMPLATE_BASEURL + "/device-template?searchText=%s" % searchText, header)
        if response != None and response["data"] != None and len(response["data"]) > 0:
            templates = response["data"]

        if len(templates) > 0:
            return templates[0]
        else:
            return None
    except:
        return None

def GetAccessToken():
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict
    global uniqueId
    global template
    global serial_number
    global EndorsementKey
    global deviceTemplateGuid
    global template_name
    #QA API
    AUTH_BASEURL = my_config_parser_dict["CloudSystemControl"]["http_auth_token"]
    TEMPLATE_BASEURL = my_config_parser_dict["CloudSystemControl"]["http_device_template"]
    DEVICE_BASEURL= my_config_parser_dict["CloudSystemControl"]["http_device_create"]
    username = my_config_parser_dict["CloudSystemControl"]["username"]
    password = my_config_parser_dict["CloudSystemControl"]["password"]
    solution_key = my_config_parser_dict["CloudSystemControl"]["solution-key"]
    ACCESS_TOKEN = get_auth(username, password, solution_key)
    if ACCESS_TOKEN == None:
        myprint("authentication failed")
        #sys.exit(1)
        return 0
    #---------------------------------------------------------------------
    template_name = "zt" + str(serial_number)
    available_name = str(my_config_parser_dict["CloudSystemControl"]["template_name"])
    if (available_name != ""):
        template_name = available_name
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    #---------------------------------------------------------------------
    # Get template attribute by searchText
    myprint("Access template " + str(template_name))
    template = get_template(template_name)
    if template != None:
        print("Device template already exist...")
        deviceTemplateGuid = template['guid']
    myprint("DeviceTemplate " + str(template))
    return 1



def CloudSetupFirmware():
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict
    global uniqueId
    global serial_number
    global EndorsementKey
    global template
    global isedge
    global isgateway
    global templateDescription
    global template_name
    global deviceTemplateGuid
    myprint("Setting up firmware")
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    firmware = []
    response = service_call("GET", my_config_parser_dict["CloudSystemControl"]["http_device_firmware"] + "/firmware/lookup", header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        firmware = response["data"]
    body = {
            "firmwareName": str(my_config_parser_dict["CloudDeviceFirmware"]["firmwarename"]).upper() + str(serial_number).upper() ,
            "firmwareDescription": str(my_config_parser_dict["CloudDeviceFirmware"]["firmwaredescription"]),
            "hardware": str(my_config_parser_dict["CloudDeviceFirmware"]["hardware"]),
            "software": str(my_config_parser_dict["CloudDeviceFirmware"]["software"]) # ,
            #"firmwarefile": str(my_config_parser_dict["CloudDeviceFirmware"]["firmwarefile"])
    }
    response = service_call("POST", my_config_parser_dict["CloudSystemControl"]["http_device_firmware"] + "/firmware" , header, body)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        myprint("Added firmware entry")
    else:
        myprint("Firmware failed" + str(response))
        sys.exit(0)
    myprint("Firmware list " +str(firmware))


def CloudConfigureDevice():
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict
    global uniqueId
    global serial_number
    global EndorsementKey
    global template
    global isedge
    global isgateway
    global templateDescription
    global template_name
    global deviceTemplateGuid
    isedge = 0
    isgateway = 0
    #---------------------------------------------------------------------
    # Create new template
    template_name = "zt" + str(serial_number)
    available_name = str(my_config_parser_dict["CloudSystemControl"]["template_name"])
    if (available_name != ""):
        template_name = available_name
    templateDescription = "SmartEdgeIIoTGateway"
    myprint(template_name)
    if (str(my_config_parser_dict["CloudSystemControl"]["isedgesupport"]) == "1"):
        templateDescription = "SmartEdgeIIoTGatewayEdge"
        isedge = 1
    if (str(my_config_parser_dict["CloudSystemControl"]["isgatewaysupport"]) == "1"):
        if (isedge == 1):
            templateDescription = "SmartEdgeIIoTGatewayEdgeGateway"
        else:
            templateDescription = "SmartEdgeIIoTGatewayGateway"
        isgateway = 1
    #CloudSetupFirmware()
    templateDescription = templateDescription + str(serial_number)
    template = None
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    if (isedge == 1):
        body = {
                "name": template_name,
                "description": str(templateDescription),
                "code": template_name,
                "isEdgeSupport": isedge,
                "isType2Support": isgateway,
                #"tag": template_name,
                "attributes": 0,
                "attrXml": 0,
                "firmwareguid":  "",
                "authType": 4
        }
    elif (isgateway == 1):
        body = {
                "name": template_name,
                "description": str(templateDescription),
                "code": template_name,
                "isEdgeSupport": isedge,
                "isType2Support": isgateway,
                "tag": template_name,
                "attributes": 0,
                "attrXml": 0,
                "firmwareguid":  "",
                "authType": 4
        }
    else:

        body = {
                "name": template_name,
                "description": str(templateDescription),
                "firmwareguid": "",
                "code": template_name,
                "isEdgeSupport": isedge,
                "authType": 4, # TPM only
        }
    response = service_call("POST", TEMPLATE_BASEURL + "/device-template", header, body)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        deviceTemplateGuid = str(response["data"][0]["deviceTemplateGuid"])

    if deviceTemplateGuid == None:
        myprint("Failed to create device template...")
        return
    myprint(deviceTemplateGuid)

    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }

    # Get attribute data types
    datatype = None
    response = service_call("GET", TEMPLATE_BASEURL + "/device-template/datatype", header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        datatype = {}
        for d in response["data"]:
            datatype[d["name"]] = d["guid"]
    myprint("len check")
    if len(datatype) == 0:
        return

    myprint("len ok")
    count = int(my_config_parser_dict["CloudSystemControl"]["defaultobjectcount"])
    #section = "CloudSDKDefaultObject"
    while (count != 0):
        header = {
                "Content-type": "application/json",
                "Accept": "*/*",
                "Authorization": ACCESS_TOKEN
        }
        if (isedge == 1):
            aggType = str(my_config_parser_dict["CloudSDKDefaultObject" + str(count)]['edgeaggregatetype'])
            Tumble = my_config_parser_dict["CloudSDKDefaultObject" + str(count)]['edgetumblingwindow']

            body = {
                    "localName": my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"],
                    "deviceTemplateGuid": deviceTemplateGuid,
                    "unit" : str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["units"]) ,
                    "description": str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["description"]),
                    "dataTypeGuid": datatype[my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["value"]],
                    "aggregateType": aggType.split(),
                    "attributes": [],
                    "tumblingWindow": Tumble

            }
        elif (isgateway == 1):
            aggType = str(my_config_parser_dict["CloudSDKDefaultObject" + str(count)]['edgeaggregatetype'])
            Tumble = my_config_parser_dict["CloudSDKDefaultObject" + str(count)]['edgetumblingwindow']

            body = {
                    "localName": my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"],
                    "deviceTemplateGuid": deviceTemplateGuid,
                    "unit" : str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["units"]) ,
                    "description": str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["description"]),
                    "dataTypeGuid": datatype[my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["value"]],
                    "aggregateType": aggType.split(),
                    "tag": template_name,
                    "attributes": [],
                    "tumblingWindow": Tumble

            }
        else:
            body = {
                    "localName": my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"],
                    "deviceTemplateGuid": deviceTemplateGuid,
                    "unit" : str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["units"]) ,
                    "description": str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["description"]),
                    "dataTypeGuid": datatype[my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["value"]]
            }
        myprint("Adding Object " + my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"])
        response = service_call("POST", TEMPLATE_BASEURL + "/template-attribute", header, body)
        if response != None and response["data"] != None:
            name = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"]
            usepythoninterface = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["usepythoninterface"]
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["name"] = name
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["usepythoninterface"] = usepythoninterface

            report = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["report"]
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["report"] = report
            reportpolltime = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["reportpolltime"]
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["reportpolltime"] = reportpolltime
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["pushdataalways"] = int(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["pushdataalways"])
        else:
            myprint("Couldn't add object")
        count = count - 1

    myprint("Added Attributes")
    count = int(my_config_parser_dict["CloudSystemControl"]["defaultcommandcount"])
    while (count != 0):
        header = {
                "Content-type": "application/json",
                "Accept": "*/*",
                "Authorization": ACCESS_TOKEN
        }

        body = {
                "name": str(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["commandname"]),
                "deviceTemplateGuid": deviceTemplateGuid,
                "command": str(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["command"]),
                "requiredParam": int(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["hasparameter"]),
                "requiredAck": int(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["requiresack"]),
                "isOTACommand": int(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["isiotcommand"]),
        }
        myprint("Adding Command " + my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["commandname"])
        response = service_call("POST", TEMPLATE_BASEURL + "/template-command", header, body)
        if response != None and response["data"] != None:
            my_command_dict[my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["command"]] = my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["usepythoninterface"]
        count = count - 1
    myprint("Commands added")

def CloudEnrollDevice():
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict
    global uniqueId
    global serial_number
    global EndorsementKey
    global template
    global isedge
    global isgateway
    global templateDescription
    global template_name
    global deviceTemplateGuid

    if deviceTemplateGuid == None:
        myprint("Cannot enroll device without template")
        return

    header = {
        "Content-type": "application/json",
        "Accept": "*/*",
        "Authorization": ACCESS_TOKEN
    }

    url = DEVICE_BASEURL + "/device/?searchText=" + uniqueId + "&customField=false" 
    response = service_call("GET", url, header)
    if response != None:
        return

    display_name = str(my_config_parser_dict["CloudSystemControl"]["display_name"])

    if not display_name:
        display_name = "IoTGateway " + str(serial_number)

    body = {
        "deviceTemplateGuid":deviceTemplateGuid,
        "displayName":display_name,
        "endorsementKey":EndorsementKey,
        "entityGuid":str(my_config_parser_dict["CloudSystemControl"]["entity_guid"]),
        "note":"test",
        "uniqueID":uniqueId
    }

    response = service_call("POST", TEMPLATE_BASEURL + "/device", header, body)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        myprint("Device enrolled")
    else:
        myprint("Device enroll failed: " + str(response))

def CloudSetupObjects():
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict, my_rules_dict
    global uniqueId
    global template
    global template_name
    global templateDescription
    global deviceTemplateGuid
    #QA API
    role = my_config_parser_dict["CloudSystemControl"]["role"]

    header = {
        "Content-type": "application/json",
        "Accept": "*/*",
        "Authorization": ACCESS_TOKEN
    }
    if template == None:
        myprint("Device template does not exist Configuring and Registering Device on Cloud!")
        CloudConfigureDevice()
        myprint("Cloud Configured")
        CloudEnrollDevice()
        template = get_template(template_name)
        return
    else:
        CloudEnrollDevice()

    # Check if our template matches our configuration
    #---------------------------------------------------------------------
    # Get attribute data types
        template = get_template(template_name)
        if template != None:
            deviceTemplateGuid = template['guid']
    myprint("CloudConfigured")
    datatype = None
    response = service_call("GET", TEMPLATE_BASEURL + "/device-template/datatype", header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        datatype = {}
        for d in response["data"]:
            datatype[d["name"]] = d["guid"]

    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    attributes = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-attribute/%s/lookup" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        attributes = response["data"]

    count = int(my_config_parser_dict["CloudSystemControl"]["defaultobjectcount"])
    #section = "CloudSDKDefaultObject"
    while (count > 0):
        name = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"]
        exists = 0
        for attr in attributes:
            if (attr["localname"] == name):
                exists = 1
                break
        if (exists == 0):
                if(isedge == 1):
                    body = {
                            "localName": name,
                            "deviceTemplateGuid": deviceTemplateGuid,
                            "description": str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["description"]),
                            "dataTypeGuid": datatype[my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["value"]],
                            "unit" : str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["units"]) ,
                            "tag": template_name
                    }
                else:
                    body = {
                            "localName": name,
                            "deviceTemplateGuid": deviceTemplateGuid,
                            "description": str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["description"]),
                            "unit" : str(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["units"]) ,
                            "dataTypeGuid": datatype[my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["value"]]
                    }
                response = service_call("POST", TEMPLATE_BASEURL + "/template-attribute", header, body)
                if response != None and response["data"] != None:
                    myprint("Created " + name)
                else:
                    myprint("Couldn't Create Attribute " + str(name))
        count = count - 1
    myprint("Template Updated")
    attributes = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-attribute/%s/lookup" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        attributes = response["data"]

    myprint("Checking for delete")
    for attr in attributes:
        count = int(my_config_parser_dict["CloudSystemControl"]["defaultobjectcount"])
        delete = 0
        while(count > 0):
            name = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"]
            if (str(attr['localname']) == str(name)):
                delete = 1
                break
            count = count - 1
        if (delete == 0):
            attributeGuid = str(attr["guid"])
            # delete this one.
            response = service_call("DELETE", TEMPLATE_BASEURL + "/template-attribute/%s" % attributeGuid, header)
            if response != None and response["data"] != None:
                myprint("Deleted " + attr["localname"])
            else:
                myprint("None Deleted")
    myprint("Attributes synced with Cloud")
    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    attributes = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-command/%s/lookup" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        attributes = response["data"]
    count = int(my_config_parser_dict["CloudSystemControl"]["defaultcommandcount"])
    while(count > 0):
        name = my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["commandname"]
        exists = 0
        for attr in attributes:
            if (attr["name"] == name):
                exists = 1
                break
        if (exists == 0):
            body = {
                "name": name,
                "deviceTemplateGuid": deviceTemplateGuid,
                "command": str(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["command"]),
                "requiredParam": int(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["hasparameter"]),
                "requiredAck": int(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["requiresack"]),
                "isOTACommand": int(my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["isiotcommand"]),
            }
            response = service_call("POST", TEMPLATE_BASEURL + "/template-command", header, body)
            if response != None and response["data"] != None:
                myprint("Created " + name)
            else:
                myprint("Couldn't Create Command " + name)
        count = count - 1
    #Delete ones not in my dictionary
    for attr in attributes:
        delete = 0
        for name in my_command_dict:
            if (attr["command"] == name):
                delete = 1
                break
        if (delete == 0):
            attributeGuid = str(attr["guid"])
            response = service_call("DELETE", TEMPLATE_BASEURL + "/template-command/%s" % attributeGuid, header)
            if response != None and response["data"] != None:
                myprint("Delete Attr " + str(attr["command"]))
            else:
                myprint("None Deleted")
    myprint("Commands synced with cloud")
    entityguid = my_config_parser_dict["CloudSystemControl"]["entity_guid"]
    entityguid = str(entityguid)
    count = int(my_config_parser_dict["CloudSystemControl"]["defaultrulecount"])
    attributes = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_rule_template"])+"/Rule" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        attributes = response["data"]
    device_name = uniqueId
    severity_levels = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_event_template"])+"/severity-level/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        severity_levels = response["data"]

    user_guid = 0
    cloud_users = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_user_template"])+"/user/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_users = response["data"]
    for item in cloud_users:
        if (item['userid'] == my_config_parser_dict["CloudSystemControl"]["username"]):
            user_guid = item['guid']

    cloud_roles = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_user_template"])+"/role/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_roles = response["data"]
    role_guid = 0
    for role in cloud_roles:
        if (role['name'] == my_config_parser_dict["CloudSystemControl"]["role"]):
            role_guid = role['guid']
    myprint("Template name: " + str(template_name) + " " + str(deviceTemplateGuid))
#    templateGuid = template['guid']

    cloud_devices = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_device_template"])+"/device/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_devices = response["data"]
    for item in cloud_devices:
        if(device_name == item['uniqueId']):
            device_guid = item['guid']

    cloud_commands = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-command/%s/lookup" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_commands = response["data"]
    while (count > 0):
        location = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["rulelocation"]
        if (location == "Local"):
            myprint("Setup Local Rule")
            my_rules_dict["CloudSDKDefaultRule"+str(count)]["name"] = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["name"]
            my_rules_dict["CloudSDKDefaultRule"+str(count)]["sensor"] = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["sensor"]
            my_rules_dict["CloudSDKDefaultRule"+str(count)]["command"] = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["command"]
            my_rules_dict["CloudSDKDefaultRule"+str(count)]["condition"] = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["condition"]
            my_rules_dict["CloudSDKDefaultRule"+str(count)]["conditionvalue"] = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["conditionvalue"]
        elif (location == "Cloud"):
            myprint("Setup Cloud Rule")
            name = my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["name"]
            create = 0
            myprint("Rule " + str(name))
        for attr in attributes:
            if (attr["name"] == name):
                create = 1
                myprint("Exists " + str(name));
                break
            if (create == 0):
                myprint("Creating")
                severity_guid = 0
                cloud_command_guid = 0
                for item in cloud_commands:
                    if(item['name'] == my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["command"]):
                        cloud_command_guid = item['guid']
                for level in severity_levels:
                    if (level["SeverityLevel"] == my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["severity"]):
                        severity_guid = level["guid"]
                body = {
                        "name": name,
                        "templateGuid": deviceTemplateGuid,
                        "ruleType": int(my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["ruletype"]),
                        "severityLevelGuid": severity_guid,
                        "conditionText": str(my_config_parser_dict["CloudSDKDefaultRule"+str(count)]["condition"]),
                        "ignorePreference": 0,
                        "entityGuid":entityguid,
                        "applyTo":"1",
                        "devices":[device_guid],
                        "roles":[role_guid],
                        "users":[user_guid],
                        "deliveryMethod":["DeviceCommand"],
                        "commandGuid": cloud_command_guid,
                        "parameterValue": "",
                        "customETPlaceHolders": {},
                }
                response = service_call("POST",str(my_config_parser_dict["CloudSystemControl"]["http_rule_template"] + "/Rule"), header, body)
                if response != None and response["data"] != None:
                    myprint("Created " + name)
                else:
                    myprint("Couldn't Create Rule " + name)
        count = count - 1;
    myprint("Rules synced with Cloud")

def OmegaCheckZWRec(zwip):
    zwrecip = cmdline("nmap -sn %s | grep 'scan report for' " % zwip)
    found = 0
    for line in zwrecip.splitlines():
        lines = line.split()
        line = "echo " + "'" + lines[4] + "'" + " | cut -d '(' -f2 | cut -d ')' -f1"
        line = cmdline(line)
        found = 1
    if (found == 0):
        myprint("NotFound")
        return 0
    return 1

def RemoveOmegaCloudAttribute(name):
    print("Removing Omega Attribute")
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict, my_rules_dict
    global uniqueId
    global template
    if template == None:
        return
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    #---------------------------------------------------------------------
    # Get attribute data types
    datatype = None
    response = service_call("GET", TEMPLATE_BASEURL + "/device-template/datatype", header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        datatype = {}
        for d in response["data"]:
            datatype[d["name"]] = d["guid"]

    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }

    if (isedge == 1):
        body = {
                "localName": name,
                "deviceTemplateGuid": deviceTemplateGuid,
                "dataTypeGuid": datatype['NUMBER'],
                "tag": template_name
        }
    else:
        body = {
                "localName": name,
                "deviceTemplateGuid": deviceTemplateGuid,
                "dataTypeGuid": datatype['NUMBER']
        }

    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    attributes = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-attribute/%s/lookup" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        attributes = response["data"]

    if len(attributes) > 0:
        for attr in attributes:
            attributeGuid = str(attr["guid"])
            if (str(attr["localname"]) == name):
                # delete this one.
                response = service_call("DELETE", TEMPLATE_BASEURL + "/template-attribute/%s" % attributeGuid, header)
                if response != None and response["data"] != None:
                    myprint("Deleted " + str(name))
                    my_sensor_dict[name]["name"] = ""
                else:
                    myprint("Deleted None")


def OmegaRsModbusScan():
    global OmegaSSLock

    import Smart_Sensor as ss
    devname = "/dev/ttySC0"
    slaves = my_config_parser_dict["OmegaSensorConfiguration"]["rs485modbusslaveaddresses"]

    with OmegaSSLock:
            for item in slaves.split():
                try:
                    myprint("Trying SlaveAddress " + str(item))
                    mydev = ss.SmartSensor(devname, int(item))
                    ss.Device.serial.baudrate = int(my_config_parser_dict["OmegaSensorConfiguration"]["rs485modbusbaud"])
                    ss.Device.serial.parity = str(my_config_parser_dict["OmegaSensorConfiguration"]["rs485modbusparity"])
                    ss.Device.serial.stopbits = int(my_config_parser_dict["OmegaSensorConfiguration"]["rs485modbusstopbits"])
                    ss.Device.serial.databits = int(my_config_parser_dict["OmegaSensorConfiguration"]["rs485modbusdatabits"])
                    sensor_count = mydev.Number_Of_Sensors(ss.Device)
                    while (sensor_count > 0):
                        AddNewOmegaCloudAttribute(devname, mydev,sensor_count,ss.Device)
                        sensor_count = sensor_count - 1
                    output_count = mydev.Number_Of_Outputs(ss.Device)
                    while (output_count > 0):
                        AddNewOmegaCloudCommand(devname, mydev, output_count, ss.Device)
                        output_count = output_count - 1
                except:
                    myprint("No Serial Communications to " + str(devname) + " SlaveAdress " + str(item))



def ProcessOmegaZWSensorTask(name):
    myprint("Processing Omega ZW " + str(name))
    global my_sensor_dict
    global uniqueId
    global sdk
    global SendDataArray
    global SendDataLock
    global OmegaZWLock
    global PushDataNow
    global PushDataArray

    zw = my_sensor_dict[name]["zwsocket"]
    try:
        while(sdk == 0):
            time.sleep(10)
        time.sleep(2)
        report = my_sensor_dict[name]["report"]
        reportpolltime = my_sensor_dict[name]["reportpolltime"]
        lastvalue = 0
        value = -1
        pushdataalways = int(my_sensor_dict[name]["pushdataalways"])
        #myprint("ProcessingZW")
        my_sensor_dict[name]["value"] = lastvalue
        while 1:
            zwip = my_sensor_dict[name]["OmegaDev"]
            zwip = str(zwip)
            zwip = zwip.strip('\r\n')
            if (OmegaCheckZWRec(zwip) == 0):
                myprint("Communications down ZWREC " + str(zwip))
                RemoveOmegaCloudAttribute(name)
                sys.exit(1)
            else:
                with OmegaZWLock:
                    value = zw.Sensor_Reading(my_sensor_dict[name]["OmegaSensorNumber"], my_sensor_dict[name]["OmegaDevice"])

                if (value == None):
                    myprint("Error reading value exiting task " +str(name))
                    sys.exit(1)
                else:
                    my_sensor_dict[name]["value"] = value
                    data = {}
                    data[my_sensor_dict[name]["name"]] = value
                    obj = {
                            "uniqueId": uniqueId,
                            "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                            "data": data
                    }
                    if (my_sensor_dict[name]["report"] == "Polled"):
                        if(pushdataalways == 1):
                            with SendDataLock:
                                PushDataArray.append(obj)
                                PushDataNow = 1
                        else:
                            with SendDataLock:
                                SendDataArray.append(obj)
                        myprint(str(name) + "=" + str(value) + " " + str(obj['time']))
                    elif (my_sensor_dict[name]["report"] == "OnChange"):
                        my_sensor_dict[name]["reportheartbeatcount"] = int(my_sensor_dict[name]["reportheartbeatcount"]) - 1
                        if (my_sensor_dict[name]["reportheartbeatcount"] == 0):
                            with SendDataLock:
                                SendDataArray.append(obj)
                                PushDataNow = 1
                            myprint(str(name) + "=" + str(value) + " " + str(obj['time']))
                            lastvalue = value
                            my_sensor_dict[name]["reportheartbeatcount"] = int(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecsensorreportheartbeatcount"])
                        else:
                            if (lastvalue != value):
                                if(pushdataalways == 1):
                                    with SendDataLock:
                                        PushDataArray.append(obj)
                                        PushDataNow = 1
                                else:
                                    with SendDataLock:
                                        SendDataArray.append(obj)
                                myprint(str(name) + "=" + str(value) + " " + str(obj['time']))
                            lastvalue = value
            time.sleep(float(reportpolltime))

    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        myprint(ex.message)
        myprint("Omega ZW-REC ExitTask")
#    except SystemExit as ex:
#        exc_type, exc_value, exc_traceback = sys.exc_info()
#        traceback.print_tb(exc_traceback)
#        myprint("Omega ZW-REC SystemExit")


def NewOmegaZWRecAttributes(zw, line, num, deviceid):
    myprint("Add ZW Attributes " + str(num) + str(zw))
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict, my_rules_dict
    global uniqueId
    global isedge
    global isgateway
    global template
    global template_name
    global ThreadCount
    global templateDescription
    role = my_config_parser_dict["CloudSystemControl"]["role"]
    if template == None:
        return
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    #---------------------------------------------------------------------
    # Get attribute data types
    datatype = None
    response = service_call("GET", TEMPLATE_BASEURL + "/device-template/datatype", header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        datatype = {}
        for d in response["data"]:
            datatype[d["name"]] = d["guid"]

    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    description = "\rOmega ZWREC Sensor"
    count = 0
    while(count < num):
        name = "ZW"+str(line).strip('\r\n')+"Device" + str(deviceid) +"Sensor" + str(count)
        name = re.sub('[^0-9a-zA-Z^]+','',name)
        name = name[:31]
        with OmegaZWLock:
            units = zw.Sensor_Units(count)
            units = re.sub('[^0-9a-zA-Z^]+','', units)
        if (isedge == 1):
            body = {
                    "localName": name,
                    "description": description,
                    "deviceTemplateGuid": deviceTemplateGuid,
                    "dataTypeGuid": datatype['NUMBER'],
                    "unit" : units,
                    "aggregateType": ["Min"],
                    "attributes": [],
                    "tumblingWindow": "1s"
            }
        elif (isgateway == 1):
            body = {
                    "localName": name,
                    "description": description,
                    "deviceTemplateGuid": deviceTemplateGuid,
                    "dataTypeGuid": datatype['NUMBER'],
                    "unit" : units ,
                    "tag": template_name,
                    "aggregateType": ["Max", "Min", "Sum", "Average"],
                    "attributes": [],
                    "tumblingWindow": "1m"
            }

        else:
            body = {
                    "localName": name,
                    "description": description,
                    "deviceTemplateGuid": deviceTemplateGuid,
                    "unit" : units,
                    "dataTypeGuid": datatype['NUMBER']
            }
        response = service_call("POST", TEMPLATE_BASEURL + "/template-attribute", header, body)
        if response != None and response["data"] != None:
            myprint("Created " + str(name))
        else:
            myprint("Already Exists Attribute " + name)
            return

        my_sensor_dict[name]["report"] = my_config_parser_dict["OmegaSensorConfiguration"]["zwrecsensorreport"]
        my_sensor_dict[name]["reportpolltime"] = my_config_parser_dict["OmegaSensorConfiguration"]["zwrecsensorreportpolltime"]

        my_sensor_dict[name]["pushdataalways"] = 0
        my_sensor_dict[name]["usepythoninterface"] = "OmegaGetValue"
        my_sensor_dict[name]["OmegaDevice"] = deviceid
        my_sensor_dict[name]["OmegaSensorNumber"] = count
        my_sensor_dict[name]["OmegaDev"] = line.strip('\r\n')
        my_sensor_dict[name]["IsOmegaDev"] = 1
        my_sensor_dict[name]["OmegaOutput"] = 0
        my_sensor_dict[name]["name"] = name
        my_sensor_dict[name]["zwsocket"] = zw
        my_sensor_dict[name]["reportheartbeatcount"] = my_config_parser_dict["OmegaSensorConfiguration"]["zwrecsensorreportheartbeatcount"]
        my_sensor_dict[name]["precision"] = int(my_config_parser_dict["OmegaSensorConfiguration"]["precision"])
        ThreadCount = ThreadCount + 1
        x = threading.Thread(target=ProcessOmegaZWSensorTask, args=(name,))
        x.daemon = True
        x.start()
        my_sensor_dict[name]["OmegaSensorTask"] = x
        count = count + 1

def OmegaNewZWRec(line):
    global ActiveIP
    global OmegaZWLock
    myprint("Line " + str(line))
    # if its in active list just skip it
    #for item in ActiveIP:
    #    if (str(item) == str(line)):
    #        print("Skiping " + str(line) + " Already active!")
    #        return
    import ZW_REC_Interface as zw

    with OmegaZWLock:
        zw.reconnect(line)
    count = 1
    while (count < 32):
        with OmegaZWLock:
            zw.get_sensor_info(count)
            num = zw.Num_Sensors()

        if (num != 0):
            NewOmegaZWRecAttributes(zw, line, num, count)
        count = count  + 1

def OmegaZWRecScan():
    global ActiveIP
    # Check only eth0 and eth1 for now
    foundline = 0
    Rescan = 0
    ScanStatic = 0
    ScanDynamic = 0
    if (str(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecconnectstatic"]) == str("Yes")):
        ScanStatic = 1
        myprint("StaticScanning")
    if (str(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecconnectdynamic"]) == str("Yes")):
        myprint("ScanDynamic")
        ScanDynamic = 1
    if (ScanStatic == 0) and (ScanDynamic == 0):
        # no scanning is configured were done.
        sys.exit(0)
    time.sleep(10)
    while 1:
        try:
            if (Rescan == 0):
                if (ScanStatic == 1):
                    myprint("Static scanning now")
                    cmd = "nmap -sn 169.254.1.* | grep 'scan report for' "
                    zwrecip = cmdline(cmd.encode())
                    for line in zwrecip.splitlines():
                        lines = line.split()
                        line = "echo " + "'" + lines[4] + "'" + " | cut -d '(' -f2 | cut -d ')' -f1"
                        line = cmdline(line.encode())
                        foundline = str(lines[4])
                        found = 0
                        for item in ActiveIP:
                            if (item == line):
                                found = 1
                        if (found == 0):
                            OmegaNewZWRec(line)
                            ActiveIP[line] = line
                if (ScanDynamic == 1):
                    foundline = 0
                    is_eth0 = cmdline("ifconfig eth0 | grep inet")
                    if (is_eth0 != ""):
                        cmd = "ip -o -f inet addr show eth0| awk '/scope global/ {print $6}' | cut -d '(' -f2 | cut -d ')' -f1"
                        subnet = cmdline(cmd.encode())
                        subnet = subnet.decode().replace("255", "*")
                        subnet = subnet.strip()
                        if (subnet.find("169.254") == -1):
                            cmd = "nmap -sn " + subnet + "| grep zwrec"
                            zwrecip = cmdline(cmd.encode())
                            myprint(zwrecip)
                            for line in zwrecip.splitlines():
                                found = 0
                                thiszw = str(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecconnectdynamicnames"])
                                if (thiszw != str("All")):
                                    for thisone in thiszw.split():
                                        if (line.find(thisone) != -1):
                                            found = 1
                                        else:
                                            myprint("NotFound " + str(thisone))
                                else:
                                    found = 1
                                if (found == 1):
                                    line = "echo " + "'" + line.strip() + "'" + " | cut -d '(' -f2 | cut -d ')' -f1"
                                    line = cmdline(line.encode())
                                    foundline = line
                                    found = 0
                                    for item in ActiveIP:
                                        if (item == line):
                                            found = 1
                                    if (found == 0):
                                        OmegaNewZWRec(line)
                                        ActiveIP[line] = line
                    is_eth1 = cmdline("ifconfig eth1 | grep inet")
                    if (is_eth1 != ""):
                        cmd = "ip -o -f inet addr show eth1| awk '/scope global/ {print $6}' | cut -d '(' -f2 | cut -d ')' -f1"
                        subnet = cmdline(cmd.encode())
                        subnet = subnet.decode().replace("255", "*")
                        subnet = subnet.strip()
                        if (subnet.find("169.254") == -1):
                            cmd = "nmap -sn " + subnet + "| grep zwrec"
                            zwrecip = cmdline(cmd.encode())
                            zwrecip = zwrecip.decode('utf-8')
                            for line in zwrecip.splitlines():
                                found = 0
                                thiszw = str(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecconnectdynamicnames"])
                                if (thiszw != str("All")):
                                    for thisone in thiszw.split():
                                        if (line.find(thisone) != -1):
                                            found = 1
                                        else:
                                            myprint("NotFound " + str(thisone))
                                    else:
                                        found = 1
                                    if (found == 1):
                                        line = "echo " + "'" + line.strip() + "'" + " | cut -d '(' -f2 | cut -d ')' -f1"
                                        line = cmdline(line.encode())
                                        foundline = line
                                        for item in ActiveIP:
                                            if (item == line):
                                                found = 1
                                        if (found == 0):
                                            OmegaNewZWRec(line)
                                            ActiveIP[line] = line

            time.sleep(60)
        except Exception as ex:
            #myprint("ZW Scan exception")
            exc_type, exc_vluue, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback)
            myprint(ex)
            sys.stdout.flush()
            sys.stderr.flush()
            sys.exit(0)

def OmegaGetValue(name):
    global OmegaSSLock
    try:
        value = -1
        count = my_sensor_dict[name]["OmegaSensorNumber"]
        mydev = my_sensor_dict[name]["OmegaDev"]
        Device = my_sensor_dict[name]["OmegaSSDevice"]
        with OmegaSSLock:
            value = mydev.Sensor_Reading(count - 1,Device)

    except:
        myprint("Omega Exception" + str(my_sensor_dict[name]["OmegaDevName"]))
        return
    return round(value, my_sensor_dict[name]["precision"])

def ProcessOmegaSensorTask(name):
    global my_sensor_dict
    global uniqueId
    global sdk
    global SendDataArray
    global SendDataLock
    global PushDataNow
    global PushDataArray

    try:
        myprint("OmegaSensorTask "+ name)
        while(sdk == 0):
            time.sleep(10)
        time.sleep(2)
        report = my_sensor_dict[name]["report"]
        reportpolltime = my_sensor_dict[name]["reportpolltime"]
        pushdataalways = int(my_sensor_dict[name]["pushdataalways"])
        lastvalue = 0
        my_sensor_dict[name]["value"] = lastvalue
        while 1:
            time.sleep(float(reportpolltime))
            value = globals()[my_sensor_dict[name]["usepythoninterface"]](name)
            if (value == None):
                # special case (? May need string to detect
                myprint("Omega reading fault! " + str(name))
                mydev = my_sensor_dict[name]["OmegaDev"]
                mydev.debug = True
                return
                #sys.exit(1)
            else:
                my_sensor_dict[name]["value"] = value
                data = {}
                data[my_sensor_dict[name]["name"]] = value
                obj = {
                        "uniqueId": uniqueId,
                        "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "data": data
                }
                if (my_sensor_dict[name]["report"] == "Polled"):
                    if(pushdataalways == 1):
                        with SendDataLock:
                            PushDataArray.append(obj)
                            PushDataNow = 1
                    else:
                        with SendDataLock:
                            SendDataArray.append(obj)
                    myprint(str(name) + "=" + str(value) + " " + str(obj['time']))
                elif (my_sensor_dict[name]["report"] == "OnChange"):
                    my_sensor_dict[name]["reportheartbeatcount"] = int(my_sensor_dict[name]["reportheartbeatcount"]) - 1
                    if (my_sensor_dict[name]["reportheartbeatcount"] == 0):
                        with SendDataLock:
                            SendDataArray.append(obj)
                            PushDataNow = 1
                        myprint(str(name) + "=" + str(value) + " " + str(obj['time']))
                        lastvalue = value
                        my_sensor_dict[name]["reportheartbeatcount"] = int(my_config_parser_dict["OmegaSensorConfiguration"]["usbsensorreportheartbeatcount"])
                    else:
                        if (lastvalue != value):
                            if(pushdataalways == 1):
                                with SendDataLock:
                                    PushDataArray.append(obj)
                                    PushDataNow = 1
                            else:
                                with SendDataLock:
                                    SendDataArray.append(obj)
                            myprint(str(name) + "=" + str(value) + " " + str(obj['time']))
                            lastvalue = value

    except Exception as ex:
        myprint("Omega Exception:" + str(ex))

    myprint("OmegaExit " + str(name))


def AddNewOmegaCloudAttribute(devname, mydev, count, Device):
    dev_id = mydev.Device_ID(Device)
    my_name = mydev.Sensor_Name(count-1,Device)
    device_name = mydev.Device_Type(Device)
    device_name = re.sub('[^0-9a-zA-Z^]+', '',device_name)
    name = str(device_name.rstrip('\0')) + str(my_name.rstrip('\0')) + str(hex(int(dev_id))).rstrip('L')
    name = name.replace(' ', '')
    name = name.replace('_','')
    name = re.sub('[^0-9a-zA-Z^]+','',name)
    name = name[:31]
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict, my_rules_dict
    global uniqueId
    global isedge
    global isgateway
    global template
    global template_name
    global ThreadCount
    global templateDescription
    role = my_config_parser_dict["CloudSystemControl"]["role"]

    if template == None:
        myprint("Device template does not exist")
        return
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    #---------------------------------------------------------------------
    # Get attribute data types
    datatype = None
    response = service_call("GET", TEMPLATE_BASEURL + "/device-template/datatype", header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        datatype = {}
        for d in response["data"]:
            datatype[d["name"]] = d["guid"]

    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    description = "\rOmega "
    description = description + "FW " + str(mydev.Firmware_Version(Device)) + " CV " + str(mydev.Core_Version(Device)) + " HW " + str(mydev.Hardware_Version(Device))
    description = description + "\rDate " + str(mydev.Manufactured_Date(Device))
    description = description + "\rCal " + str(mydev.Calibration_Date(Device))
    description = description + "\rMin " + str(mydev.Sensor_Min_Value(count - 1,Device)) + " Max " + str(mydev.Sensor_Max_Value(count - 1, Device)) + " RMin " + str(mydev.Sensor_Min_Range(count - 1,Device)) + "RMax " + str(mydev.Sensor_Max_Range(count - 1,Device))
    description = description + "\rPrecision " + str(mydev.Sensor_Precision(count - 1,Device)) + " Measure " + str(mydev.Sensor_Measurement(count - 1,Device)) + " Gain " + str(mydev.Sensor_Scale_Gain(count - 1,Device)) + " Offset " + str(mydev.Sensor_Scale_Offset(count - 1,Device))
    units = str(mydev.Sensor_Units(count - 1, Device))
    #units = "TBD"
    units = re.sub('[^0-9a-zA-z^]+', '_',units)
    my_sensor_dict[name]["precision"] = int(mydev.Sensor_Precision(count - 1,Device))
    if (isedge == 1):
        body = {
                "localName": name,
                "description": description,
                "deviceTemplateGuid": deviceTemplateGuid,
                "dataTypeGuid": datatype['NUMBER'],
                "unit" : str(units),
                "aggregateType": ["Min"],
                "attributes": [],
                "tumblingWindow": "1s"
        }
    elif (isgateway == 1):
        body = {
                "localName": name,
                "description": description,
                "deviceTemplateGuid": deviceTemplateGuid,
                "dataTypeGuid": datatype['NUMBER'],
                "unit" : str(units),
                "tag": template_name,
                "aggregateType": ["Max", "Min", "Sum", "Average"],
                "attributes": [],
                "tumblingWindow": "1m"
        }
    else:
        body = {
                "localName": name,
                "description": description,
                "deviceTemplateGuid": deviceTemplateGuid,
                "unit": str(units),
                "dataTypeGuid": datatype['NUMBER']
        }
    response = service_call("POST", TEMPLATE_BASEURL + "/template-attribute", header, body)
    if response != None and response["data"] != None:
        myprint("Created " + str(name))
    else:
        myprint("Already Exists Attribute " + name)
    my_sensor_dict[name]["precision"] = int(mydev.Sensor_Precision(count - 1,Device))
    my_sensor_dict[name]["report"] = my_config_parser_dict["OmegaSensorConfiguration"]["usbsensorreport"]
    my_sensor_dict[name]["reportpolltime"] = my_config_parser_dict["OmegaSensorConfiguration"]["usbsensorreportpolltime"]
    my_sensor_dict[name]["reportheartbeatcount"] = int(my_config_parser_dict["OmegaSensorConfiguration"]["usbsensorreportheartbeatcount"])
    my_sensor_dict[name]["usepythoninterface"] = "OmegaGetValue"
    my_sensor_dict[name]["pushdataalways"] = 0
    my_sensor_dict[name]["OmegaDevice"] = name
    my_sensor_dict[name]["OmegaSensorNumber"] = count
    my_sensor_dict[name]["OmegaDev"] = mydev
    my_sensor_dict[name]["OmegaDevName"] = devname
    my_sensor_dict[name]["OmegaOutput"] = 0
    my_sensor_dict[name]["name"] = name
    my_sensor_dict[name]["IsOmegaDevice"] = 1
    my_sensor_dict[name]["OmegaSSDevice"] = Device
    ThreadCount = ThreadCount + 1
    x = threading.Thread(target=ProcessOmegaSensorTask, args=(name,))
    x.daemon = True
    x.start()
    my_sensor_dict[name]["OmegaSensorTask"] = x



def AddNewOmegaCloudCommand(devname, mydev, count,Device):
    dev_id = mydev.Device_ID(Device)
    my_name = mydev.Output_Name(count-1,Device)
    device_name = mydev.Device_Type(Device)
    name = str(device_name) + '' + str(my_name) + '' + str(hex(int(dev_id)))
    name = name.replace(' ', '')
    name = re.sub('[^0-9a-wyzA-Z^]+','',str(name))
    name = name[:28]	# Reserve 3 bytes for Set or Clr
    myprint("Adding Omega Command")

    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict, my_rules_dict
    global uniqueId
    global template
    global deviceTemplateGuid
    role = my_config_parser_dict["CloudSystemControl"]["role"]

    if template == None:
        myprint("No Omega template on cloud!!")
        return
    #---------------------------------------------------------------------


    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    body = {
            "name": str(name) + "Set" ,
            "deviceTemplateGuid": deviceTemplateGuid,
            "command": "OmegaCommand " + str(name) + " 100",
            "requiredParam": 0,
            "cmdText" : str(name) + "100",
            "requiredAck": 0,
            "isOTACommand": 0,
    }
    response = service_call("POST", TEMPLATE_BASEURL + "/template-command", header, body)
    if response != None and response["data"] != None:
        myprint("Omega command added")
    else:
        myprint("Couldnt add command " + str(name))
    body = {
            "name": str(name) + "Clr" ,
            "deviceTemplateGuid": deviceTemplateGuid,
            "command": "OmegaCommand " + str(name) + " 0",
            "requiredParam": 0,
            "cmdText" : str(name) + "0",
            "requiredAck": 0,
            "isOTACommand": 0,
    }

    response = service_call("POST", TEMPLATE_BASEURL + "/template-command", header, body)
    if response != None and response["data"] != None:
        my_sensor_dict[name]["OmegaDevice"] = name
        my_sensor_dict[name]["OmegaSensorNumber"] = count
        my_sensor_dict[name]["OmegaDev"] = mydev
        my_sensor_dict[name]["OmegaDevName"] = devname
        my_sensor_dict[name]["OmegaOutput"] = 1
        my_sensor_dict[name]["OmegaSSDevice"] = Device
        my_sensor_dict[name]["name"] = name
    else:
        myprint("Couldnt add command " + str(name))

def RemoveOmegaCloudCommand(name):
    global ACCESS_TOKEN,AUTH_BASEURL,TEMPLATE_BASEURL,DEVICE_BASEURL
    global my_config_parser_dict, my_sensor_dict, my_command_dict, my_rules_dict
    global uniqueId
    global template
    global deviceTemplateGuid
    if template != None:
        print("")
    else:
        return
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    #---------------------------------------------------------------------
    # get attributes first
    header = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": ACCESS_TOKEN
    }
    cloud_commands = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-command/%s" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_commands = response["data"]
    else:
        temp = 0
    if len(cloud_commands) > 0:
        for attr in cloud_commands:
            if (attr['name'].find(name) == 0):
                attributeGuid = str(attr["guid"])
                response = service_call("DELETE", TEMPLATE_BASEURL + "/template-command/%s" % attributeGuid, header)
                if response != None and response["data"] != None:
                    myprint("Deleted " + str(name))
                else:
                    myprint("None")



def OmegaUsbRemoved(devname):
    global my_sensor_dict
    for item in my_sensor_dict:
        if ( 'OmegaDevName' in my_sensor_dict[item]):
            if ((my_sensor_dict[item]['OmegaDevName'] == devname) and (my_sensor_dict[item]['OmegaOutput'] == 0)):
                x = my_sensor_dict[item]['OmegaSensorTask']
                myprint("SYSEX " + str(item))
                ctype_async_raise(x,SystemExit)
                time.sleep(1)
                RemoveOmegaCloudAttribute(my_sensor_dict[item]['name'])
            if ((my_sensor_dict[item]['OmegaDevName'] == devname) and (my_sensor_dict[item]['OmegaOutput'] == 1)):
                RemoveOmegaCloudCommand(my_sensor_dict[item]['name'])
                mydev = my_sensor_dict[item]['OmegaDev']
                del mydev

def AddOmegaRules(devname):
    global my_sensor_dict
    global my_config_parser_dict
    global ACCESS_TOKEN
    global deviceTemplateGuid
    myprint("Adding Omega Rules")
    count = int(my_config_parser_dict["CloudSystemControl"]["defaultomegarulecount"])
    myprint("Omega rule count " + str(count))
    entityguid = my_config_parser_dict["CloudSystemControl"]["entity_guid"]
    entityguid = str(entityguid)
    #count = int(my_config_parser_dict["CloudSystemControl"]["defaultrulecount"])
    header = {
        "Content-type": "application/json",
        "Accept": "*/*",
        "Authorization": ACCESS_TOKEN
    }
    attributes = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_rule_template"])+"/Rule" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        attributes = response["data"]
    device_name = uniqueId
    severity_levels = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_event_template"])+"/severity-level/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        severity_levels = response["data"]

    user_guid = 0
    cloud_users = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_user_template"])+"/user/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_users = response["data"]
    for item in cloud_users:
        if (item['userid'] == my_config_parser_dict["CloudSystemControl"]["username"]):
            user_guid = item['guid']

    cloud_roles = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_user_template"])+"/role/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_roles = response["data"]
    role_guid = 0
    for role in cloud_roles:
        if (role['name'] == my_config_parser_dict["CloudSystemControl"]["role"]):
            role_guid = role['guid']
    cloud_devices = []
    response = service_call("GET", str(my_config_parser_dict["CloudSystemControl"]["http_device_template"])+"/device/lookup" , header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_devices = response["data"]
    for item in cloud_devices:
        if(device_name == item['uniqueId']):
            device_guid = item['guid']
    cloud_commands = []
    response = service_call("GET", TEMPLATE_BASEURL + "/template-command/%s" % deviceTemplateGuid, header)
    if response != None and response["data"] != None and len(response["data"]) > 0:
        cloud_commands = response["data"]
    while (count != 0):
        location = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["rulelocation"]
        if (location == "Local"):
            myprint("Setup Local Rule")
            my_rules_dict["CloudSDKCustomOmegaRule"+str(count)]["name"] = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["name"]
            my_rules_dict["CloudSDKCustomOmegaRule"+str(count)]["sensor"] = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["sensor"]
            my_rules_dict["CloudSDKCustomOmegaRule"+str(count)]["command"] = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["command"]
            my_rules_dict["CloudSDKCustomOmegaRule"+str(count)]["condition"] = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["condition"]
            my_rules_dict["CloudSDKCustomOmegaRule"+str(count)]["conditionvalue"] = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["conditionvalue"]
        elif (location == "Cloud"):
            myprint("Setup Cloud Rule")
            name = my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["name"]
            create = 0
            myprint("Rule " + str(name))
            for attr in attributes:
                if (attr["name"] == name):
                    create = 1
                    myprint("Exists " + name);
                    break
                if (create == 0):
                    myprint("Creating")
                    severity_guid = 0
                    cloud_command_guid = 0
                    for item in cloud_commands:
                        if(item['name'] == my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["command"]):
                            cloud_command_guid = item['guid']
                    for level in severity_levels:
                        if (level["SeverityLevel"] == my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["severity"]):severity_guid = level["guid"]
                    body = {
                            "name": name,
                            "templateGuid": deviceTemplateGuid,
                            "ruleType": "1", #my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["ruletype"],
                            "severityLevelGuid": severity_guid,
                            "conditionText": my_config_parser_dict["CloudSDKCustomOmegaRule"+str(count)]["condition"],
                            "ignorePreference": 0,
                            "entityGuid":entityguid,
                            "applyTo":"1",
                            "devices":[device_guid],
                            "roles":[role_guid],
                            "users":[user_guid],
                            "deliveryMethod":["DeviceCommand"],
                            "commandGuid": cloud_command_guid,
                            "parameterValue": "",
                            "customETPlaceHolders": {},
                    }
                    response = service_call("POST", str(my_config_parser_dict["CloudSystemControl"]["http_rule_template"] + "/Rule"), header, body)
                    if response != None and response["data"] != None:
                        myprint("Created " + name)
                    else:
                        myprint("Couldn't Create Rule " + name)
        count = count - 1;
    myprint("Rules synced with Cloud")



def OmegaUsb(devname):
    global OmegaSSLock
    myprint("OmegaUsb " + str(devname) )
    time.sleep(1)
    import Smart_Sensor as ss
    if ( OmegaSSLock.locked() == True ):
        OmegaSSLock.release()
        #myprint(my_sensor_dict.keys())
        for item in list(my_sensor_dict.keys()):
            #myprint(my_sensor_dict[item])
            for item2 in my_sensor_dict:
                #myprint(item)
                myprint(item2)
                #if (my_sensor_dict[item2]['IsOmegaDevice'] == 1 ):
                #    del my_sensor_dict[item]['OmegaSSDev']
        myprint("Releasing Lock")

    with OmegaSSLock:
        debugging = int(my_config_parser_dict["OmegaSensorConfiguration"]["enabledebug"])
        mydev = ss.SmartSensor(devname,1, debugging)
        myprint("Opened ")
        sensor_count = mydev.Number_Of_Sensors(ss.Device)
        myprint("SensorCount Read")
        while (sensor_count > 0):
            AddNewOmegaCloudAttribute(devname, mydev,sensor_count,ss.Device)
            sensor_count = sensor_count - 1
        output_count = mydev.Number_Of_Outputs(ss.Device)
        while (output_count > 0):
            AddNewOmegaCloudCommand(devname, mydev, output_count,ss.Device)
            output_count = output_count - 1

    myprint("OmegaUsb End")
    AddOmegaRules(devname)

def CheckForUsb():
    global Aquired_Usb
    # some function to run on insertion of usb
    usbdevs = usbinfo.usbinfo()
    for item in usbdevs:
        if (item['iProduct'] == "ZW-USB"):
            found = 0
            new_omega_dev = str(item['devname'])
            if (new_omega_dev.find('ACM') > 0):
                for item1 in Aquired_Usb:
                    for item2 in Aquired_Usb[item1]:
                        if (item2 == new_omega_dev):
                            found = 1
                if (found == 1):
                    myprint("Already Found")
                    del new_omega_dev
                    continue
                Aquired_Usb['ZW-USB'][new_omega_dev] = new_omega_dev
                OmegaUsb(new_omega_dev)

def RemoveForUsb():
    global Aquired_Usb
    # some function to run on insertion of usb
    usbdevs = usbinfo.usbinfo()
    for item1 in Aquired_Usb["ZW-USB"]:
        found = 0
        for item in usbdevs:
            if (item['iProduct'] == "ZW-USB"):
                new_omega_dev = str(item['devname'])
                if (new_omega_dev.find('ACM') > 0):
                    if (item1 == item['devname']):
                        found = 1
        if (found == 0):
            new_omega_dev = item1
            OmegaUsbRemoved(str(new_omega_dev))
            Aquired_Usb['ZW-USB'][new_omega_dev] = 0

class USBDetector():
    ''' Monitor udev for detection of usb '''
    global ThreadCount
    def __init__(self):
        ''' Initiate the object '''
        global ThreadCount
        ThreadCount = ThreadCount + 1
        thread = threading.Thread(target=self._work)
        thread.daemon = True
        thread.start()

    def _work(self):
        global Aquired_Usb
        global ThreadCount
        ''' Runs the actual loop to detect the events '''
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='usb')
        # this is module level logger, can be ignored
        self.monitor.start()
        for device in iter(self.monitor.poll, None):
            if device.action == 'add':
                CheckForUsb()
            else:
                # some function to run on removal of usb
                RemoveForUsb()


def SetupDigitalOutputs():
    if os.path.isdir("/sys/class/gpio/gpio201"):
        dummy = 1
    else:
        os.system("echo 201 >/sys/class/gpio/export")
        os.system("echo 203 >/sys/class/gpio/export")
        os.system("echo 205 >/sys/class/gpio/export")
        os.system("echo 207 >/sys/class/gpio/export")
        os.system("echo out >/sys/class/gpio/gpio201/direction")
        os.system("echo out >/sys/class/gpio/gpio203/direction")
        os.system("echo out >/sys/class/gpio/gpio205/direction")
        os.system("echo out >/sys/class/gpio/gpio207/direction")

#
# Predefined functions for commands.
#

def EnableRESTApi(args):
    os.system("systemctl enable restservice")
    os.system("systemctl start restservice")

def DisableRESTApi(args):
    os.system("systemctl disable restservice")
    os.system("systemctl stop restservice")

def EnableLedService(args):
    os.system("systemctl enable ledservice")
    os.system("systemctl start ledservice")

def DisableLedService(args):
    os.system("systemctl disable ledservice")
    os.system("systemctl stop ledservice")

def EnableButtonService(args):
    os.system("systemctl enable buttonservice")
    os.system("systemctl start buttonservice")

def DisableButtonService(args):
    os.system("systemctl disable buttonservice")
    os.system("systemctl stop buttonservice")

def EnableSSH(args):
    os.system("systemctl enable ssh")
    os.system("service ssh start")

def DisableSSH(args):
    os.system("service ssh stop")
    os.system("systemctl disable ssh")

def SwitchToConfiguration(args):
    os.system("/bin/bash /opt/avnet-iot/iotservices/switch_configuration_mode")

def SetDigitalOutput1Now(args):
    os.system("echo 1 >/sys/class/gpio/gpio201/value")

def ClearDigitalOutput1Now(args):
    os.system("echo 0 >/sys/class/gpio/gpio201/value")

def SetDigitalOutput2Now(args):
    os.system("echo 1 >/sys/class/gpio/gpio203/value")

def ClearDigitalOutput2Now(args):
    os.system("echo 0 >/sys/class/gpio/gpio203/value")

def SetDigitalOutput3Now(args):
    os.system("echo 1 >/sys/class/gpio/gpio205/value")

def ClearDigitalOutput3Now(args):
    os.system("echo 0 >/sys/class/gpio/gpio205/value")

def SetDigitalOutput4Now(args):
    os.system("echo 1 >/sys/class/gpio/gpio207/value")

def ClearDigitalOutput4Now(args):
    os.system("echo 0 >/sys/class/gpio/gpio207/value")


def RebootNow(msg):
    os.system("/bin/bash /opt/avnet-iot/iotservices/reboot")

def FactoryDefaultNow(msg):
    os.system("/bin/bash /opt/avnet-iot/iotservices/switch_factory_reset")

#
# Predefined functions for sensors
#
def GetTheTemp():
    global my_sensor_dict
    file_handle = open('/sys/class/thermal/thermal_zone0/temp', 'r')
    line = file_handle.readline()
    CpuTemperature =  float(float(line)/float(1000))
    file_handle.close()
    #for section in my_sensor_dict:
    #    if section[name] == 'CpuTemperature':
    #        CpuTemperature = round(CpuTemperature, section[name]["precision"])
    return CpuTemperature

def GetTheFreq():
    file_handle = open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r')
    line = file_handle.readline()
    CpuFrequency = old_div(int(line)/100000)
    file_handle.close()
    return(CpuFrequency)

def SetupDigitalInputs():
    if os.path.isdir("/sys/class/gpio/gpio200"):
        dummy = 1
    else:
        os.system("echo 200 >/sys/class/gpio/export")
        os.system("echo 202 >/sys/class/gpio/export")
        os.system("echo 204 >/sys/class/gpio/export")
        os.system("echo 206 >/sys/class/gpio/export")

def GetDigitalInput1():
    file = open('/sys/class/gpio/gpio200/value','r')
    value = file.readline()
    file.close()
    return int(value)

def GetDigitalInput2():
    file = open('/sys/class/gpio/gpio202/value','r')
    value = file.readline()
    file.close()
    return int(value)

def GetDigitalInput3():
    file = open('/sys/class/gpio/gpio204/value','r')
    value = file.readline()
    file.close()
    return int(value)

def GetDigitalInput4():
    file = open('/sys/class/gpio/gpio206/value','r')
    value = file.readline()
    file.close()
    return int(value)

global ThreadsRunningLast
ThreadsRunningLast = {}

def ProcessMonitor():
    global ThreadsRunningLast
    running = cmdline("ps -aux | grep python | grep example")
    for line in running.splitlines():
        lines = line.split()
        if (str(lines[10]) == str("python")):
            pid = str(lines[1])
            pidcmd = str("ps -T %s | wc" % pid)
            countstr = cmdline(str(pidcmd))
            countstr = countstr.split()
            return int(countstr[0])
    return 0

def FreeMemory():
    memory = cmdline("free -m")
    for line in memory.splitlines():
        lines = line.split()
        if (str(lines[0]) == str("Mem:")):
            return int(lines[6])
    return 0

def CpuUtilization():
    percent = psutil.cpu_percent()
    return int(percent)

def FreeDisk():
    disk = cmdline("df")
    for line in disk.splitlines():
        lines = line.split()
        if (str(lines[0]) == str("/dev/root")):
            return int(lines[3])
    return 0

def SystemHealth():
    global MessageCount
    result = str("MsgCount= " + str(MessageCount) + " CpuUtil= " + str(CpuUtilization()) + " FreeDsk= " + str(FreeDisk()) + " FreeMem= " + str(FreeMemory()) + " Python thrds= " + str(ProcessMonitor()))
    return result

def ProcessRules(name):
    global my_rules_dict
    global my_sensor_dict
    try:
        for rulename in my_rules_dict:
            for sensorname in my_sensor_dict:
                if (my_sensor_dict[sensorname]["name"] == name):
                    break
                if( name == my_rules_dict[rulename]["sensor"]):
                    condition = str(my_rules_dict[rulename]["condition"])
                    conditionvalue = int(my_rules_dict[rulename]["conditionvalue"])
                    if (condition == "IsEqualTo"):
                        if (my_sensor_dict[sensorname]["value"] == conditionvalue):
                            globals()[my_rules_dict[rulename]["command"]]()
                    elif (condition == "IsNotEqualTo"):
                        if (my_sensor_dict[sensorname]["value"] != conditionvalue):
                            globals()[my_rules_dict[rulename]["command"]]()
                    elif (condition == "IsGreaterThan"):
                        if (my_sensor_dict[sensorname]["value"] > conditionvalue):
                            globals()[my_rules_dict[rulename]["command"]]()
                    elif (condition == "IsGreaterOrEqualTo"):
                        if (my_sensor_dict[sensorname]["value"] >= conditionvalue):
                            globals()[my_rules_dict[rulename]["command"]]()
                    elif (condition == "IsLessThan"):
                        if (my_sensor_dict[sensorname]["value"] < conditionvalue):
                            globals()[my_rules_dict[rulename]["command"]]()
                    elif (condition == "IsLessOrEqualTo"):
                        if (my_sensor_dict[sensorname]["value"] < conditionvalue):
                            globals()[my_rules_dict[rulename]["command"]]()
                    else:
                        myprint("Unknown Condition" + condition)
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        myprint(ex.message)
    except KeyboardInterrupt:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        myprint(ex.message)


def ProcessSensorTask(name):
    global my_sensor_dict
    global sdk
    global uniqueId
    global SendDataArray
    global SendDataLock
    global PushDataNow
    global PushDataArray

    try:
        myprint("SensorTask "+ str(my_sensor_dict[name]["name"]))
        report = my_sensor_dict[name]["report"]
        reportpolltime = my_sensor_dict[name]["reportpolltime"]
        lastvalue = globals()[my_sensor_dict[name]["usepythoninterface"]]()
        pushdataalways = int(my_sensor_dict[name]["pushdataalways"])
        my_sensor_dict[name]["value"] = lastvalue
        while 1:
            value = globals()[my_sensor_dict[name]["usepythoninterface"]]()
            if (value == None):
                myprint("Error reading value, exiting task " + str(name))
                sys.exit(1)
            else:
                my_sensor_dict[name]["value"] = value
                data = {}
                if (int(my_config_parser_dict[name]["precision"]) != 0):
                    data[my_sensor_dict[name]["name"]] = round(float(value), int(my_config_parser_dict[name]["precision"]))
                else:
                    data[my_sensor_dict[name]["name"]] = value
                obj = {
                    "uniqueId": uniqueId,
                    "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "data": data
                }
                if (my_sensor_dict[name]["report"] == "Polled"):
                    if(pushdataalways == 1):
                        with SendDataLock:
                            PushDataArray.append(obj)
                            PushDataNow = 1
                    else:
                        with SendDataLock:
                            SendDataArray.append(obj)
                    myprint(str(my_sensor_dict[name]["name"]) + "=" + str(value) + " " + str(obj['time']).rstrip('\n'))
                elif (my_sensor_dict[name]["report"] == "OnChange"):
                    my_sensor_dict[name]["reportheartbeatcount"] = int(my_sensor_dict[name]["reportheartbeatcount"]) - 1
                    if (my_sensor_dict[name]["reportheartbeatcount"] == 0):
                        with SendDataLock:
                            SendDataArray.append(obj)
                            PushDataNow = 1
                        myprint(str(my_sensor_dict[name]["name"]) + "=" + str(value) + " " + str(obj['time']).rstrip('\n'))
                        lastvalue = value
                        my_sensor_dict[name]["reportheartbeatcount"] = int(my_config_parser_dict[name]["reportheartbeatcount"])
                    else:
                        if (lastvalue != value):
                            if(pushdataalways == 1):
                                with SendDataLock:
                                    PushDataArray.append(obj)
                                    PushDataNow = 1
                            else:
                                with SendDataLock:
                                    SendDataArray.append(obj)
                            myprint(str(my_sensor_dict[name]["name"]) + "=" + str(value) + " " + str(obj['time']).rstrip('\n'))
                            lastvalue = value
            ProcessRules(my_sensor_dict[name]["name"])
            time.sleep(float(reportpolltime))
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        myprint(ex.message)
        myprint("Exception in ProcessSensorTask")
    except KeyboardInterrupt:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        myprint(ex.message)
        myprint("Exception in ProcessSensorTask")

def MonitorSDKStartupError(item):
    global IoTConnectConnecting
    while(1):
        time.sleep(30)
        if (IoTConnectConnecting == 1):
            myprint("failed to connect, letting systemd restart us")
            os._exit(0)



def SendDataToCloud(name):
    global sdk
    global SendDataArray
    global SendDataLock
    global PushDataNow
    global PushDataArray
    global my_config_parser_dict
    global MessageCount
    RefreshBasicToken = 0
    myprint("Sending to cloud Task started")
    green = 1
    count = int(my_config_parser_dict["CloudSystemControl"]["sendtocloudrate"])
    try:
        while(True):
            ledprocess = cmdline("/opt/avnet-iot/iotservices/iotstat | grep led")
            if (ledprocess == ""):
                if (green == 1):
                    os.system('echo 0 >/sys/class/leds/red/brightness')
                    os.system('echo 1 >/sys/class/leds/green/brightness')
                    green = 0
                else:
                    os.system('echo 0 >/sys/class/leds/red/brightness')
                    os.system('echo 0 >/sys/class/leds/green/brightness')
                    green = 1
            time.sleep(1)
            #gc.collect()
            RefreshBasicToken = RefreshBasicToken + 1
            if (RefreshBasicToken > int(my_config_parser_dict["CloudSystemControl"]["renewaccesstoken"])):
                myprint("Refreshing Access Token")
                AccessOK = GetAccessToken()
                RefreshBasicToken = 0
            if (sdk == 0):
                continue
            count = count - 1
            if (PushDataNow == 1):
                with SendDataLock:
                    PushDataNow = 0
                    if (len(PushDataArray) != 0):
                        MessageCount = MessageCount + 1
                        sdk.SendData(PushDataArray)
                        PushDataArray = []
            if (count == 0):
                count = int(my_config_parser_dict["CloudSystemControl"]["sendtocloudrate"])
                if (len(SendDataArray) != 0):
                    with SendDataLock:
                        MessageCount = MessageCount + 1
                        sdk.SendData(SendDataArray)
                        SendDataArray = []
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
        myprint(ex)
        myprint("SendDataToCloud Exit")


def ConnAckWatcher():
    try:
        while 1:
            out = subprocess.Popen(['journalctl', '-n', '1', '-u', 'iotconnectservice'], stdout=PIPE)
            stdoutdata, stderrdata = out.communicate()
            if "mqtt_client timed out waiting for CONNACK" in stdoutdata:
                myprint("Azure SDK error (Conn Ack), restarting IoTConnect to fix..")
                os._exit(0)
            if "Connection Not Accepted: 0x5: Not Authorized" in stdoutdata:
                myprint("Cloud connection error, restarting IoTConnect service to try to fix.  Also, please check your subscription status.")
                os._exit(0)
            time.sleep(1)
    except Exception as ex:
        myprint("Exception in ConnAckWatcher: " + str(ex))


def Watchdogthread():
    myprint(cmdline('/opt/avnet-iot/iotservices/startwd'))
    myprint("Using ATTINY Watchdog pet every 30 seconds")
    while 1:
        time.sleep(int(my_config_parser_dict["CloudSystemControl"]["useiotwatchdog"]))
        cmdline('echo t | tee /dev/watchdog1')
    myprint("Stopping ATTINY Watchdog.")
    myprint(cmdline('echo V | tee /dev/watchdog1'))


def callbackTwinMessage(msg):
    if msg:
        myprint(json.dumps(msg))


def main(argv):
    global my_config_parser_dict
    global cpId
    global uniqueId
    global EndorsementKey
    global serial_number
    global my_sensor_dict
    global my_command_dict
    global sdk
    global template
    global template_name
    global ThreadCount
    global IoTConnectConnecting
    try:
        result = Popen(
                    args="/opt/avnet-iot/iotservices/tpm_device_provision < crlf.txt",
                    stdout=PIPE,
                    shell=True
        )
        id_ek = result.communicate()[0]
        if (result.returncode != 0):
            # Can't access TPM, try again
            time.sleep(1)
            result = Popen(
                        args="/opt/avnet-iot/iotservices/tpm_device_provision < crlf.txt",
                        stdout=PIPE,
                        shell=True
            )
            id_ek = result.communicate()[0]
	    if (result.returncode != 0):
                myprint("Can't Access TPM, restarting")
                os.system("/bin/bash /opt/avnet-iot/iotservices/reboot")
        lines = id_ek.splitlines()
        uniqueId = lines[3]
        uniqueId = uniqueId.decode('utf-8')
        EndorsementKey = lines[6]
        EndorsementKey = EndorsementKey.decode('utf-8')
        serialn = cmdline("grep Serial /proc/cpuinfo").rstrip()
        serial_number = str(serialn[-8:])
        serial_number = serial_number.decode('utf-8')

        config = configparser.ConfigParser()
        config.read('IoTConnectSDK.conf.default')
        my_config_parser_dict = {s:dict(config.items(s)) for s in config.sections()}
        #myprint(my_config_parser_dict)

        config.read('IoTConnectSDK.conf')
        my_config_parser_current_dict = {s:dict(config.items(s)) for s in config.sections()}
        my_config_parser_dict.update(my_config_parser_current_dict)

        scopeId = str(my_config_parser_dict["CloudSDKConfiguration"]["scopeid"])
        env = str(my_config_parser_dict["CloudSDKConfiguration"]["env"])
        cpId = str(my_config_parser_dict["CloudSDKConfiguration"]["cpid"])
        if (int(my_config_parser_dict["CloudSystemControl"]["enabledebug"]) == 0):
            sys.stdout = open('/dev/null', 'w')
            sys.stderr = open('/dev/null', 'w')
        else:
            try:
                sys.stdout = open(my_config_parser_dict["CloudSystemControl"]["debuglogfile"], 'a')
                sys.stderr = open(my_config_parser_dict["CloudSystemControl"]["debuglogfile"], 'a')
                print("Logging to " + str(my_config_parser_dict["CloudSystemControl"]["debuglogfile"]))
                myprint("Log start")
            except Exception as ex:
                print("Could not enable logging: " + str(ex))
                sys.stdout = open('/dev/null', 'w')
                sys.stderr = open('/dev/null', 'w')
        #
        # Setup sensor dictionary.
        #
        IoTConnectConnecting = 1

        AccessOK = GetAccessToken()
        if (AccessOK == 0):
            myprint("Authentication issue add username/password to IoTConnectSDK.conf to enable autoconfiguration and PNP. Skipping cloud sync")
        count = int(my_config_parser_dict["CloudSystemControl"]["defaultobjectcount"])
        while (count != 0):
            name = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["name"]
            usepythoninterface = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["usepythoninterface"]
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["name"] = name
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["usepythoninterface"] = usepythoninterface
            report = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["report"]
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["report"] = report
            reportpolltime = my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["reportpolltime"]
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["reportheartbeatcount"] = int(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["reportheartbeatcount"])
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["pushdataalways"] = int(my_config_parser_dict["CloudSDKDefaultObject"+str(count)]["pushdataalways"])
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["reportpolltime"] = reportpolltime
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["OmegaOutput"] = 0
            my_sensor_dict["CloudSDKDefaultObject"+str(count)]["IsOmegaDevice"] = 0
            count = count - 1

        #
        # Setup command dictionary.
        #
        count = int(my_config_parser_dict["CloudSystemControl"]["defaultcommandcount"])
        while (count != 0):
            my_command_dict[my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["command"]] = my_config_parser_dict["CloudSDKDefaultCommand"+str(count)]["usepythoninterface"]
            count = count - 1

        #
        # Setup/adjust cloud attributes/commands/rules
        #
        if (AccessOK == 1):
            CloudSetupObjects()
            time.sleep(5)
        #
        # Setup our inputs/outputs
        #
        SetupDigitalInputs()
        SetupDigitalOutputs()
        #
        # Call user initializations
        #
        try:
            execfile("user_functions.py",globals())
            globals()['user_Initialize']()
        except Exception as ex:
            myprint("Failed running user functions: " + str(ex))
        #
        # Start scanning for custom Omega ZW-REC devices.
        x5 = threading.Thread(target=ConnAckWatcher, name='Journal Watcher')
        x5.daemon = True
        x5.start()

        #
        if ((str(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecconnectstatic"]) == str("Yes")) or (str(my_config_parser_dict["OmegaSensorConfiguration"]["zwrecconnectdynamic"]) == str("Yes"))):
            if (AccessOK == 1):
                y = threading.Thread(target=OmegaZWRecScan)
                y.daemon = True
                y.start()
            #else:
            #    myprint("Please add username/password to IoTConnectSDK.conf for Omega Plug&Play")
        #
        # Check USB for SmartSensor device.
        #
        if (AccessOK == 1):
            CheckForUsb()
            usb = USBDetector()
        else:
            myprint("Please add username/password to IoTConnectSDK.conf for USB Plug&Play")
        #
        # Check RS485 bus for SmartSensor device.
        #
        if (str(my_config_parser_dict["OmegaSensorConfiguration"]["rs485modbus"]) == str("Yes")):
            if (AccessOK == 1):
                OmegaRsModbusScan()
            else:
                myprint("Please add username/password to IoTConnectSDK.conf for RS485 Plug&Play")
        x = threading.Thread(target=MonitorSDKStartupError, args=("TPM issue thread",))
        x.daemon = True
        x.start()
        if (int(my_config_parser_dict["CloudSystemControl"]["useiotwatchdog"]) == 1):
            x1 = threading.Thread(target=Watchdogthread)
            x1.daemon = True
            x1.start()
        #
        # Connect to cloud and start processing data
        while 1:
        #
            with IoTConnectSDK(cpId, uniqueId, scopeId, callbackMessage, callbackTwinMessage, env) as sdk:
                try:
                    IoTConnectConnecting = 0
                    os.system('touch /tmp/iotconnect.txt')
                    ThreadCount = 0
                    devices = sdk.GetAttributes()
                    if len(devices) == 0:
                        myprint("Warning: Cloud device has no attributes")
                    ThreadCount = ThreadCount + 1
                    x2 = threading.Thread(target=SendDataToCloud, args=("Sending",))
                    x2.daemon = True
                    x2.start()
                    count = int(my_config_parser_dict["CloudSystemControl"]["defaultobjectcount"])
                    while (count != 0):
                        ThreadCount = ThreadCount + 1
                        x3 = threading.Thread(target=ProcessSensorTask, args=("CloudSDKDefaultObject"+str(count), ))
                        x3.daemon = True
                        x3.start()
                        count = count - 1
                    # Just keep running....
                    while 1:
                        time.sleep(60)

                except KeyboardInterrupt:
                    sys.exit(0)
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback)
#        myprint("Exiting in 10 seconds: " + str(ex))
#        time.sleep(10)
    finally:
        myprint("Quitting")
        os.system('rm -f /tmp/iotconnect.txt')
    os._exit(0)

if __name__ == "__main__":
    main(sys.argv)
