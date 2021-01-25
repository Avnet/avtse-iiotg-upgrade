import minimalmodbus
import serial
import Smart_Sensor_IPSO as IPSO
import Smart_Sensor_Registers as ss_reg
from time import sleep

class SmartSensor:
   

    def __init__(self, port, address = 1, debug = False):
        '''
        Establish a Smart Sensor connection using Smart Sensor USB adaptor
        '''
        global Device
        minimalmodbus.BAUDRATE = 38400
        minimalmodbus.PARITY = serial.PARITY_EVEN
        minimalmodbus.TIMEOUT = 0.5
        Device = minimalmodbus.Instrument(port, address)
        #print(Device)
        if (debug == True):
            Device.debug = True
            print("Device Setup", Device)

    def Device_ID(self,Device):
        '''
        Returns the Device ID as a 64 bit value
        '''
        sleep(float(0.03))
        xx = Device.read_registers(ss_reg.Register("DEVICE_ID"), 4)
        value = xx[0]
        value = (value << 16) + xx[1]
        value = (value << 16) + xx[2]
        value = (value << 16) + xx[3]
        return value

    def Device_Type(self,Device):
        '''
        Returns the Device Type string name
        '''
        
        sleep(float(0.03))
        xx = Device.read_registers(ss_reg.Register("DEVICE_NAME_STRING"),8)
        name_bytes = str((chr(xx[0] & 0xff))) + str((chr(xx[1] >> 8))) + str((chr(xx[1] & 0xff))) + str((chr(xx[2] >> 8))) + str((chr(xx[2] & 0xff))) + str((chr(xx[3] >> 8))) + str((chr(xx[3] & 0xff))) + str((chr(xx[4] >> 8))) + str((chr(xx[4] & 0xff)))
	#print("NameBytes")
        #print(name_bytes)
        return (name_bytes)

    def Firmware_Version(self,Device):
        '''
        Returns the Hardware version as 'xxx.xxx.xxx.xxx'
        '''
        sleep(float(0.03))
        xstr = Device.read_long(ss_reg.Register("FIRMWARE_VERSION"))
        return Serial_Number_To_String(xstr)
       
    def Core_Version(self,Device):
        '''
        Returns the Core version as 'xxx.xxx.xxx.xxx'
        '''
        sleep(float(0.03))
        xstr = Device.read_long(ss_reg.Register("CORE_VERSION"))
        return Serial_Number_To_String(xstr)
       
    def Hardware_Version(self,Device):
        '''
        Returns the Hardware version as 'xxx.xxx.xxx.xxx'
        '''
        sleep(float(0.03))
        xstr = Device.read_long(ss_reg.Register("HARDWARE_VERSION"))
        return Serial_Number_To_String(xstr)

    def User_Hours(self,Device):
        '''
        Returns the number of hours since last reset
        '''
        sleep(float(0.03))
        return (Device.read_register(ss_reg.Register("USER_HOURS")))

    def Manufactured_Date(self,Device):
        '''
        Returns the Manufactured date as "YYYY/MN/DY"
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("MANUFACTURED_DATE"))
        return Date_To_String(xstr)
        

    def Operating_Time(self,Device):
        '''
        Returns the total time under power as DDDDD-HH:MM:SS
        '''
        sleep(float(0.03))
        xstr = Device.read_long(ss_reg.Register("OPERATING_TIME"))
        return Time_To_String(xstr)

    def Calibration_Date(self,Device):
        '''
        Returns the Calibraion date as "YYYY/MN/DY"
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("CALIBRATION_DATE"))
        return Date_To_String(xstr)

    def Calibration_Time(self,Device):
        '''
        Returns the total time since calibration as DDDDD-HH:MM:SS
        '''
        sleep(float(0.03))
        xstr = Device.read_long(ss_reg.Register("CALIBRATION_TIME"))
        return Time_To_String(xstr)
        
    def Event_0_Timebase(self,Device):
        ''' 
        Returns Event 0 timebase, typically the number of seconds between sensor updates
        '''
        sleep(float(0.03))
        return (Device.read_register(ss_reg.Register("EVENT_0_TIMEBASE")))

    def Event_1_Timebase(self,Device):
        ''' 
        Returns Event 1 timebase
        '''
        sleep(float(0.03))
        return (Device.read_register(ss_reg.Register("EVENT_1_TIMEBASE")))

    def Number_Of_Sensors(self,Device):
        '''
        Returns the number of active sensors
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("NUMOFSENSORS_OUTPUTS"))
        return ((xstr >> 8) & 0xff)

    def Number_Of_Outputs(self,Device):
        '''
        Returns the number of active outputs
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("NUMOFSENSORS_OUTPUTS"))
        return (xstr & 0xff)

    def Operating_Voltage(self,Device):
        '''
        Returns the number of active outputs
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("OPERATING_TEMP_VOLTAGE"))
        return ((xstr & 0xff) / 10)

    def Operating_Temperature(self,Device):
        '''
        Returns the number of active outputs
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("OPERATING_TEMP_VOLTAGE"))
        return ((xstr >> 8) & 0xff)

    def Fault_Process(self,Device):
        '''
        Returns the number of active outputs
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("FAULT_PROCESS_CODE"))
        return ((xstr >> 8) & 0xff)

    def Fault_Code(self,Device):
        '''
        Returns the number of active outputs
        '''
        sleep(float(0.03))
        xstr = Device.read_register(ss_reg.Register("FAULT_PROCESS_CODE"))
        return ((xstr >> 8) & 0xff)

    def Current_Time(self,Device):
        '''
        Returns the current time as DDDDD-HH:MM:SS
        '''
        sleep(float(0.03))
        xstr = Device.read_long(ss_reg.Register("CURRENT_TIME"))
        return Time_To_String(xstr)

    def Device_Name(self,Device):
        sleep(float(0.03))
        xstr = Device.read_string(ss_reg.Register("DEVICE_NAME"), 16)
        return (xstr)

    # Sensor Information
    #-------------------

    def Sensor_Name(self, sensor,Device):
        '''
        Return the user assigned name of a sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_string(ss_reg.Register("SENSOR_0_NAME"),8)
        elif (sensor == 1):
            return Device.read_string(ss_reg.Register("SENSOR_1_NAME"),8)
        elif (sensor == 2):
            return Device.read_string(ss_reg.Register("SENSOR_2_NAME"),8)
        elif (sensor == 3):
            return Device.read_string(ss_reg.Register("SENSOR_3_NAME"),8)

    def Output_Name(self, sensor,Device):
        '''
        Return the user assigned name of a sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_string(ss_reg.Register("OUTPUT_0_NAME"),8)
        elif (sensor == 1):
            return Device.read_string(ss_reg.Register("OUTPUT_1_NAME"),8)
        elif (sensor == 2):
            return Device.read_string(ss_reg.Register("OUTPUT_2_NAME"),8)
        elif (sensor == 3):
            return Device.read_string(ss_reg.Register("OUTPUT_3_NAME"),8)

    def Sensor_Min_Value(self, sensor,Device):
        '''
        Return the minimum VALUE measured by the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_MINVALUE"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_MINVALUE"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_2_MINVALUE"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_3_MINVALUE"))
        else:
            return (none)
        end


    def Sensor_Max_Value(self, sensor,Device):
        '''
        Return the maximum Value measured by the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_MAXVALUE"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_MAXVALUE"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_2_MAXVALUE"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_3_MAXVALUE"))
        else:
            return (none)
 
    def Sensor_Min_Range(self, sensor,Device):
        '''
        Return the minimum RANGE measured by the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_MINRANGE"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_MINRANGE"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_2_MINRANGE"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_3_MINRANGE"))
         
    def Sensor_Max_Range(self, sensor,Device):
        '''
        Return the maximum RANGE measured by the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_MAXRANGE"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_MAXRANGE"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_2_MAXRANGE"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_3_MAXRANGE"))
        else:
            return (none)
 
    def Sensor_Precision(self, sensor,Device):
        '''
        Return the PRECISION measured by the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_register(ss_reg.Register("SENSOR_0_PRECISION"))
        elif (sensor == 1):
            return Device.read_register(ss_reg.Register("SENSOR_1_PRECISION"))
        elif (sensor == 2):
            return Device.read_register(ss_reg.Register("SENSOR_2_PRECISION"))
        elif (sensor == 3):
            return Device.read_register(ss_reg.Register("SENSOR_3_PRECISION"))
        
    def Sensor_Measurement(self, sensor,Device):
        '''
        Return the meaurement type of the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return IPSO.Measurement_Type(Device.read_register(ss_reg.Register("SENSOR_0_IPSO_TYPE")))
        elif (sensor == 1):
            return IPSO.Measurement_Type(Device.read_register(ss_reg.Register("SENSOR_1_IPSO_TYPE")))
        elif (sensor == 2):
            return IPSO.Measurement_Type(Device.read_register(ss_reg.Register("SENSOR_2_IPSO_TYPE")))
        elif (sensor == 3):
            return IPSO.Measurement_Type(Device.read_register(ss_reg.Register("SENSOR_3_IPSO_TYPE")))

    def Sensor_Max_Range(self, sensor,Device):
        '''
        Return the maximum RANGE measured by the sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_MAXRANGE"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_MAXRANGE"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_2_MAXRANGE"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_3_MAXRANGE"))
        else:
            return (none)
 
    def Sensor_Scale_Gain(self, sensor,Device):
        '''
        Return the GAIN scaling factor for the specified sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_SCALE_GAIN"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_SCALE_GAIN"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_1_SCALE_GAIN"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_1_SCALE_GAIN"))
       
    def Sensor_Scale_Offset(self, sensor,Device):
        '''
        Return the GAIN scaling factor for the specified sensor
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_SCALE_OFFSET"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_SCALE_OFFSET"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_1_SCALE_OFFSET"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_1_SCALE_OFFSET"))
      
        
    def Sensor_Reading(self, sensor,Device):
        '''
        Read a selected sensor reading
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_float(ss_reg.Register("SENSOR_0_DATA"))
        elif (sensor == 1):
            return Device.read_float(ss_reg.Register("SENSOR_1_DATA"))
        elif (sensor == 2):
            return Device.read_float(ss_reg.Register("SENSOR_2_DATA"))
        elif (sensor == 3):
            return Device.read_float(ss_reg.Register("SENSOR_3_DATA"))
        else:
            return (none)
        
    def wait_system_ready(Device, max_wait=3):
        """
            Poll sensor until it is ready, optional timeout value
        :param max_wait: timeout in seconds
        """
        wait_time = 0.2
        while max_wait > 0:
            try:
                s = Device.read_register(0xf012)
                #if Device.device_ready:
                #    break
            except:
                pass
            time.sleep(wait_time)
            max_wait -= wait_time

        
    def SoftReset(self, sensor, Device):
        """
            Soft Reset the sensor
        """

        Device.write_register(0xf013, 4)
        Device.wait_system_ready()

    def FactoryReset(self, sensor, Device):
        """
            Factory reset the sensor
        """
        Device.write_register(0xf013, 5)
        Device.wait_system_ready()
        
    def PowerReset(sensor, Device):
        """
            Power Reset the sensor
        """

        Device.write_register(0xf013, 6)
        Device.wait_system_ready()

    def Sensor_Reset(self, sensor,ResetType, Device):
        if (ResetType == 0):
            FactoryReset(sensor, Device)
        if (ResetType == 1):
            PowerReset(sensor, Device)
        if (ResetType == 2):
            SoftReset(sensor, Device)
            

        
    def Output_Data(self, sensor, value,Device):
        '''
        Read a selected sensor reading
        '''
        sleep(float(0.03))
        print("OutputSensor " + str(sensor) + "Value " + str(value))
        if (sensor == 0):
            return Device.write_float(ss_reg.Register("OUTPUT_0"), value)
        elif (sensor == 1):
            return Device.write_float(ss_reg.Register("OUTPUT_1"), value)
        elif (sensor == 2):
            return Device.write_float(ss_reg.Register("OUTPUT_2"), value)
        elif (sensor == 3):
            return Device.write_float(ss_reg.Register("OUTPUT_3"), value)
        else:
            return (none)
 
    def Sensor_Units(self, sensor,Device):
        '''
        Read the selected sensor units
        '''
        sleep(float(0.03))
        if (sensor == 0):
            return Device.read_string(ss_reg.Register("SENSOR_0_UNITS"),2)
        elif (sensor == 1):
            return Device.read_string(ss_reg.Register("SENSOR_1_UNITS"),2)
        elif (sensor == 2):
            return Device.read_string(ss_reg.Register("SENSOR_2_UNITS"),2)
        elif (sensor == 3):
             return Device.read_string(ss_reg.Register("SENSOR_3_UNITS"),2)
        else:
            return (none)
 

    pass



def Serial_Number_To_String(serial_num):
    '''
    Converts serial number to string format (xxx.xxx.xxx.xxx)
    '''
    return('{0}.{1}.{2}.{3}'.format(((serial_num >> 24) & 0xff),
                                        ((serial_num >> 16) & 0xff),
                                        ((serial_num >> 8) & 0xff),
                                        ((serial_num >> 0) & 0xff)))

def Date_To_String(date):
    ''' 
    Converts a date to a string format (YYYY/MM/DD)
    '''
    str = '{0:0>4}/{1:0>2}/{2:0>2}'.format((((date>> 9) & 0xff) + 2000),
                                            ((date >> 5) & 0x0f),
                                            (date & 0x1f))
    return (str)

def Time_To_String(xstr):
    '''
    Converts a time to string format (DDD-HR:MN:SS)
    '''
    secs = int(xstr % 60)
    xstr = xstr / 60
    mins = int(xstr % 60)
    xstr = xstr / 60
    hours = int(xstr % 24)
    days = int(xstr / 24)
    str = '{0}-{1:0>2}:{2:0>2}:{3:0>2}'.format(days, hours, mins, secs)
    return (str)


