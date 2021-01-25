import socket

global s
global Current_Sensor_Reading
global Current_Sensor_Units
global Current_NumSensors
global port
global opened
opened = 0
port = 2000
Current_NumSensors = 0
Current_Sensor_Reading= ["NAN", "NAN", "NAN", "NAN"]
Current_Sensor_Units = ['','','','']

def reconnect(serverip):
    global s
    global port
    global opened
    try:
        if (opened == 0):
            s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((serverip, port))
        else:
            print("Already opened")
            opened = 1
    except:
        return 1
    #print("ExitReconnect")
    return 0

def get_sensor_info(end_device):
    global s
    s.settimeout(10)
    global Current_NumSensors
    global Current_Sensor_Reading
    global Current_Sensor_Units 
    try:
        #print("GetSensorInfo")
        Current_NumSensors = 0
        Current_Sensor_Reading= ["NAN", "NAN", "NAN", "NAN"]
        Current_Sensor_Units = ['','','','']
        rqst_str = "ERDB{:03}".format(end_device)
        s.send(rqst_str.encode())
        resp_str = s.recv(100)
        tokens = resp_str.split()
        if ((len(tokens)) > 3):
            Current_Sensor_Reading[0] = float(tokens[3])
            Current_Sensor_Units[0] = str(tokens[4])
            Current_NumSensors = 1
        if ((len(tokens)) > 5):
            Current_Sensor_Reading[1] = float(tokens[5])
            Current_Sensor_Units[1] = str(tokens[6])
            Current_NumSensors = 2
        if ((len(tokens)) > 7):
            Current_Sensor_Reading[2] = float(tokens[7])
            Current_Sensor_Units[2] = str(tokens[8])
            Current_NumSensors = 3

        if ((len(tokens)) > 9):
            Current_Sensor_Reading[3] = float(tokens[9])
            Current_Sensor_Units[3] = str(tokens[10])
            Current_NumSensors = 4
    except:
        return 1
    return 0

 

def Num_Sensors():
    global Current_NumSensors
    return (Current_NumSensors)

def Sensor_Reading(sensor, end_device = None):
    global Current_Sensor_Reading
    try:
        if (end_device != None):
            get_sensor_info(end_device)
            return (Current_Sensor_Reading[sensor])
    except:
        exit
def Sensor_Readings(sensor, end_device = None):
    global Current_Sensor_Reading
    if (end_device != None):
        get_sensor_info(end_device)
    return (Current_Sensor_Reading)

def Sensor_Units(sensor, end_device = None):
    global Current_Sensor_Units
    if (end_device != None):
        get_sensor_info(end_device)
    return (Current_Sensor_Units[sensor])

