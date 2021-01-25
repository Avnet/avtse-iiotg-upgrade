#!/bin/bash

ZIPFILE="$1"

# Exit with error if we are not root
if [[ "$(id -u)" != "0" ]]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

function extract_image_file ()
{
  unzip -n "$ZIPFILE"
}

function verify_image_file ()
{
  unzip -p "$ZIPFILE" | md5sum > "tmp.md5"
  echo "md5sum of the customer image file '$FILE_NAME':"
  cat "tmp.md5"
  read -p "Does md5sum match expected? [y N]?" choice
  case "$choice" in
    y|Y )
      mv "tmp.md5" "$FILE_NAME.md5"
      return 0 ;;
    *   ) return 1 ;;
  esac
}

function verify_image ()
{
  unzip -p "$ZIPFILE" | md5sum > "tmp.md5"
  diff "tmp.md5" "$FILE_NAME.md5"
  if [ $? -ne 0 ]; then
    return 1;
  else
    return 0;
  fi
}

if [ $# -lt "1" ]; then
  echo "Usage: Please specify zip file containing the customer image"
  exit 1
fi

if [ ! -f "$ZIPFILE" ]; then
  echo "Error: $ZIPFILE not found"
  exit 2
fi

# Verify zip has one file and record its length
regex="([A-Za-z0-9._%+-]+)\s+[-]+\s+[-]+\s+([0-9]+)\s+([0-9]+) file.?$"

zipfilelist=$(unzip -l $ZIPFILE)

if [ $? -ne 0 ]; then
  echo "$ZIPFILE does not appear to be a valid zipfile"
  exit 3
else
  if [[ $zipfilelist =~ $regex ]]; then
    FILE_NAME="${BASH_REMATCH[1]}"
    IMAGE_SIZE_IN_BYTES="${BASH_REMATCH[2]}"
    NUM_ZIP_FILES="${BASH_REMATCH[3]}"
    if [ "$NUM_ZIP_FILES" -ne "1" ]; then
      echo "Error: Zip file must only have one file, the image file"
      echo $zipfilelist
      exit 5
    fi
    echo "Found image file: $FILE_NAME size=$IMAGE_SIZE_IN_BYTES"
  else
    echo "Error: Unexpected Zip file listing output"
    echo $zipfilelist
    exit 4
  fi
fi

if [ ! -f "$FILE_NAME" ]; then
  extract_image_file
fi

if [ ! -f "$FILE_NAME.md5" ]; then
  echo "No md5 signature of image was found. Must perform an initial image validation."
  read -p "Ready to perform validation? [Y n]?" choice
  case "$choice" in
    n|N ) exit 9 ;;
    *   )
      verify_image_file
      if [ $? -ne 0 ]; then
        echo "Error: Image file not validated, cannot continue."
        exit 6
      fi
      ;;
  esac
fi

rm tmp.md5 2> /dev/null

gpio_base=208
mcu_spi_cs=$((gpio_base+0))
mcu_resetn=$((gpio_base+1))
failed=0

if [ ! -d /sys/class/gpio/gpio${mcu_spi_cs} ]; then echo "${mcu_spi_cs}" | tee "/sys/class/gpio/export" > /dev/null 2>&1; fi

echo high | tee "/sys/class/gpio/gpio${mcu_spi_cs}/direction" > /dev/null 2>&1
echo 1 | tee "/sys/class/gpio/gpio${mcu_spi_cs}/value" > /dev/null 2>&1

results=$(verify_image)
if [ $? -ne 0 ]; then
  echo "Error: Image file doesn't match expected md5sum"
  echo $results
  exit 1
fi

#load dtoverlay for ATtiny
result=$(dtoverlay avnet-iot-mcu.dtbo)

if [ $? -ne 0 ]; then
  echo "Could not load overlay to write to ATtiny"
  echo $result
  failed=1
else
  sleep 1

result=$(/opt/avnet-iot/utilities/attiny/avrdude -q -p attiny88 -C /opt/avnet-iot/utilities/attiny/avrdude_working.conf -c avnet_iot_spi -P /dev/spidev2.2:/dev/gpiochip4:1 -v -U flash:w:$FILE_NAME:i 2>&1 /dev/null)

  if [ $? -ne 0 ]; then
    #retry once
    result=$(/opt/avnet-iot/utilities/attiny/avrdude -q -p attiny88 -C /opt/avnet-iot/utilities/attiny/avrdude_working.conf -c avnet_iot_spi -P /dev/spidev2.2:/dev/gpiochip4:1 -v -U flash:w:$FILE_NAME:i 2>&1 /dev/null)

    if [ $? -ne 0 ]; then
      echo "Programming Failed! Review output for errors."
      echo $result
      failed=1
    fi
  fi
fi

sleep 1

if [ ! -d /sys/class/gpio/gpio${mcu_resetn} ]; then echo "${mcu_resetn}" | tee "/sys/class/gpio/export" > /dev/null 2>&1; fi

echo high | tee "/sys/class/gpio/gpio${mcu_resetn}/direction" > /dev/null 2>&1
echo 1 | tee "/sys/class/gpio/gpio${mcu_resetn}/value" > /dev/null 2>&1


echo 0 | tee "/sys/class/gpio/gpio${mcu_spi_cs}/value" > /dev/null 2>&1

echo "${mcu_spi_cs}" | tee "/sys/class/gpio/unexport" > /dev/null 2>&1
echo "${mcu_resetn}" | tee "/sys/class/gpio/unexport" > /dev/null 2>&1

#remove overlay for ATtiny
dtoverlay -R avnet-iot-mcu

if [ $failed == 0 ]; then
  echo "Passed - ATtiny programming"
  #set user led to green/red slow flash
#  i2cset -y 1 0x33 0x05 0x80
#  i2cset -y 1 0x33 0x04 0x71
  exit 0
else
  echo "Failed - ATtiny programming"
fi

exit 20
