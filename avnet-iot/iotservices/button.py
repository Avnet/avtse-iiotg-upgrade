#!/usr/bin/env python

import os
import threading
import time
from time import sleep

def check_switch_short(lock):
    try:
    	while 1:
            os.system("cat /dev/button")
            with lock:
                print("SwitchShort Resetting")
                os.system("/bin/bash -c '/opt/avnet-iot/iotservices/switch_reset'")
    except Exception as ex:
        print("Reset Button Exception:" + str(ex))

def check_switch_long(lock):
    try:
        while 1:
            os.system("cat /dev/reset")
            with lock:
                print("LongPress Resetting to Configuration State")
                os.system("/bin/bash -c '/opt/avnet-iot/iotservices/switch_configuration_mode'")
    except Exception as ex:
        print("Ap Mode Button Exception:" + str(ex))

def check_switch_factory(lock):
    try:
        while 1:
            os.system("cat /dev/factoryreset")
            with lock:
                print("WARNING!!! LongPress Resetting to Factory State WARNING!!!")
                os.system("/bin/bash -c '/opt/avnet-iot/iotservices/switch_factory_reset'")
    except Exception as ex:
        print("Factory Button Exception:" + str(ex))

if __name__ == '__main__':
    print("Starting button service")
    print(os.path.exists('/dev/button'))

    SwitchLock = threading.Lock()
    t = threading.Thread(target=check_switch_long, args=(SwitchLock,))
    t.start()
    t1 = threading.Thread(target=check_switch_short, args=(SwitchLock,))
    t1.start()
    t2 = threading.Thread(target=check_switch_factory, args=(SwitchLock,))
    t2.start()
    while 1:
        time.sleep(60*60)
