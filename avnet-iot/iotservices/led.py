#!/usr/bin/env python

import json
import os
import socket
import subprocess

from subprocess import PIPE,Popen

from shutil import copyfile
from subprocess import call
from time import sleep
import time, threading
import datetime

ApMode = 0
GreenThisTime = 0
RedThisTime = 0

GREEN_LED ='/sys/class/leds/green/brightness'
RED_LED = '/sys/class/leds/red/brightness'

#os.system('chmod 666 /sys/class/leds/red/brightness')
#os.system('chmod 666 /sys/class/leds/green/brightness')

def green_led_on():
    os.system('echo 1 > /sys/class/leds/green/brightness')
    print("GON")
    sleep(0.2)

def green_led_off():
    os.system('echo 0 > /sys/class/leds/green/brightness')
    print("GOF")
    sleep(0.2)

def red_led_on():
    os.system('echo 1 > /sys/class/leds/red/brightness')
    print("RON")
    sleep(0.2)

def red_led_off():
    os.system('echo 0 > /sys/class/leds/red/brightness')
    print("ROF")
    sleep(0.2)

def get_ap_mode():
    global ApMode
    try:
	hostapd = subprocess.call(['systemctl', 'is-active', 'hostapd.service'], stdout=None , stderr=None)
        if hostapd == 0:
            ApMode = 1
        else:
            ApMode = 0
    except Exception as ex:
        print(ex)
        ApMode = 0
    print("AP status" + str(ApMode))
    return ApMode

def check_switch():
    global GreenThisTime
    global RedThisTime
    global ApMode
    GreenFirst = 1
    time.sleep(3)
    try:
        while 1:
            get_ap_mode()
            time.sleep(1)
	    if (ApMode == 1):
                if RedThisTime == 1:
                    RedThisTime = 0
                    red_led_off()
                    green_led_on()
                else:
                    RedThisTime = 1
                    green_led_off()
                    red_led_on()
            else:
		if(GreenFirst == 1):
                    red_led_off()
		    GreenFirst == 0
                if GreenThisTime == 1:
                    GreenThisTime = 0
                    green_led_on()
                else:
                    GreenThisTime = 1
                    green_led_off()
    except Exception as ex:
        print(ex)

if __name__ == '__main__':
    print("Starting LED service")
    ApMode = 1
    red_led_off()
    green_led_on()
    GreenThisTime = 1
    t2 = threading.Thread(name='child procs', target=check_switch)
    t2.start()
    while 1:
        time.sleep(60*60)
    red_led_off()
    green_led_off()
