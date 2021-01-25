#!/bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root"
  exit 1
fi

sleep 5

if [ -c /dev/cdc-wdm0 ]; then
  # Cell modem exists
  if [ ! -f /etc/apn.conf ]; then
    echo "/etc/apn.conf not found. Waiting for user configuration..."
    # issue with qmi_wwan driver crashing if not connected, so bring down interface
    # quectel-CM will bring up the interface
    ifconfig wwan0 down
    while [ ! -f /etc/apn.conf ]; do
      sleep 30
    done
  fi

  # if mPCIe modem is in a bad state, we can reset it to recover.  Let's do that as part
  # of this script:
  gpio_base=208
  mcu_rstin_n=$((gpio_base+2))
  if [ ! -d /sys/class/gpio/gpio${mcu_rstin_n} ]; then echo "${mcu_rstin_n}" | tee "/sys/class/gpio/export" >/dev/null 2>&1; fi
  echo high | tee "/sys/class/gpio/gpio${mcu_rstin_n}/direction" >/dev/null 2>&1
  echo 0 | tee "/sys/class/gpio/gpio${mcu_rstin_n}/value" >/dev/null 2>&1
  echo 1 | tee "/sys/class/gpio/gpio${mcu_rstin_n}/value" >/dev/null 2>&1
  echo "${mcu_rstin_n}" | tee "/sys/class/gpio/unexport" >/dev/null 2>&1
  sleep 10

  # We have cell modem and APN, so try to start
  echo "Starting quectel service for APN $(cat /etc/apn.conf)"
  quectel-CM -s "$(cat /etc/apn.conf)"

else
  # No cell modem device.  Wait here since if we exit the script will restart.
  while [ ! -c /dev/cdc-wdm0 ]; do
    sleep 60
  done
fi
