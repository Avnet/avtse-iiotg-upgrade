import minimalmodbus
import Smart_Sensor as ss
import time

comport = "COM42"
print("Simple Smart Sensor Demo application, Version 1.0")
#print()
#Newport = input("Enter Comm port to use (default is {}): ".format(comport))
#if (Newport != ''):
#    comport = Newport
comport='/dev/ttyACM0'
mydev = ss.SmartSensor(comport, 1)

print("-----------Device Information------------")
#print("Device: ", mydev.Device_Type())
print("Device ID: {0:x}".format(mydev.Device_ID()))
print("Firmware Version: ", mydev.Firmware_Version())
print("Hardware Version: ", mydev.Hardware_Version())
print("Core Version: ", mydev.Core_Version())
print
print("Manufactured: ", mydev.Manufactured_Date())
print("Total Operating Time: ", mydev.Operating_Time())
print
print("Calibrated: ", mydev.Calibration_Date())
print("Time since Calibration: ", mydev.Calibration_Time())
print(".....Press ENTER to continue >")
input()
print()

print("-----------Device Configuration------------")
print("Device Name: ", mydev.Device_Name())
print("User Operation time: {} hours".format(mydev.User_Hours()))
print("Device Update rate: {} second" .format( mydev.Event_0_Timebase()))
print("Number of sensors: ", mydev.Number_Of_Sensors())
print("Number of outputs: ", mydev.Number_Of_Outputs())
print("Operating Voltage: {} volts" .format(mydev.Operating_Voltage()))
print("Operating Temperature: {} oC" .format(mydev.Operating_Temperature()))
print("Last Fault (Process): ",format(mydev.Fault_Process()))
print("Last Fault (Error Code): ",format(mydev.Fault_Code()))
print(".....Press ENTER to continue >")
input()
print()

print("-----------Sensor Configurations------------")
for SensorNum in range (0,4):
    print("---Sensor {} ---".format(SensorNum))
    print("Name: ", mydev.Sensor_Name(SensorNum))
    measurement_type = mydev.Sensor_Measurement(SensorNum)
    print("Measurement: {0}".format(measurement_type))
    if (measurement_type != None):
        print("Range: {0:.2f} to {1:.2f} {2}, Precision: {3} decimal point".format(mydev.Sensor_Min_Range(SensorNum),
                                                                 mydev.Sensor_Max_Range(SensorNum),
                                                                 mydev.Sensor_Units(SensorNum),
                                                                 mydev.Sensor_Precision(SensorNum)))
        print("Minimum value read: {0:.2f}, Maximum value read: {1:.2f}".format(mydev.Sensor_Min_Value(SensorNum),
                                                                        mydev.Sensor_Max_Value(SensorNum)))
        print("Scale Gain: {0:.2f}, Offset: {1:.2f}".format(mydev.Sensor_Scale_Gain(0),
                                                            mydev.Sensor_Scale_Offset(0)))
    print()

print("-----------Sensor Activity------------")

xx = 'G'

while (xx != 'E'):
    print(mydev.Current_Time())

    for SensorNum in range (0, 4):
        print ("{0}: {1:.2f} {2}".format(mydev.Sensor_Name(SensorNum),
                                            mydev.Sensor_Reading(SensorNum),
                                            mydev.Sensor_Units(SensorNum)))
    print(".....Press ENTER to get new readings, E to exit >")
    xx = input()
    if (xx == 'E') | (xx == 'Exit'):
        xx = 'E'
   





