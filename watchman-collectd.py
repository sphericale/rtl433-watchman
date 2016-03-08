#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import subprocess
import sys
import re
import time
from socket import gethostname
import math
import os
import threading

if os.name == 'nt': # windows
   rtl_433_cmd = r"k:\SDR\rtl\rtl_433.exe -l 0 -R 42 -F csv" # set path to rtl_433 here
else:
   rtl_433_cmd = "/usr/local/bin/rtl_433 -l 0 -R 42 -F csv" # linux

hostname = gethostname()

watchman_id = "140539678" # this needs to be set appropriately for your sensor

# tank height in cm
tank_height = 115
# tank capacity in litres
tank_capacity = 1000
# 1 = rectangle, 2 = sphere
tank_shape = 1
# currently only rectangular is implemented

# kerosene
expansion_coeff = 0.00099

#To adjust for fluid expansion
#Report volume/percentage as they would be at 10 C
canon_temp = 10

watchman_level = "U"
watchman_temperature = "U"
watchman_volume = "U"
watchman_pct = "U"

# 2016-03-07 20:59:56,Oil Watchman,140539678,,,1.667,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,128,28,0,47,,,,,,,,,,,,,,,,

watchman_re = re.compile(r'^[\d\- :]+,Oil Watchman,{},+([\d.]+),+(\d+),(\d+),(\d+),(\d+)'.format(watchman_id))

interval = 10
elapsed = 0

#l = threading.Lock()

def watch_rtl433():
    for line in iter(p.stdout.readline, b''):
        m = watchman_re.match(line)
        if m is not None:
#            l.acquire()
            global watchman_level
            global watchman_temperature
            global watchman_volume
            global watchman_pct
            watchman_level = m.group(5)
            watchman_temperature = m.group(1)
            watchman_pct_float = ((tank_height - float(watchman_level)) / tank_height) * 100
            watchman_pct = str(watchman_pct_float)
            watchman_volume = str((watchman_pct_float / 100) * tank_capacity)

            # adjust for temperature
            temp_delta = canon_temp - float(watchman_temperature)

            # delta V = V_0 Beta (t1 - t0)
            watchman_volume_float = float(watchman_volume)
            watchman_volume = str(watchman_volume_float + (watchman_volume_float * expansion_coeff * temp_delta))

            watchman_pct_float = float(watchman_pct)
            watchman_pct = str(watchman_pct_float + (watchman_pct_float * expansion_coeff * temp_delta))
#            l.release()

p = subprocess.Popen(rtl_433_cmd.split(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
t = threading.Thread(target=watch_rtl433)
t.start()

try:
    while True:
       time.sleep(1)
       if p.poll() is not None:
          break
       elapsed += 1
       if elapsed % interval == 0:
#          l.acquire()
          print("PUTVAL \"{}/exec-watchman/oiltank_temperature-oil_temperature\" interval={} N:{}".format(hostname,interval,watchman_temperature))
          print("PUTVAL \"{}/exec-watchman/oiltank_pct-oil_percent\" interval={} N:{}".format(hostname,interval,watchman_pct))
          print("PUTVAL \"{}/exec-watchman/oiltank_volume-oil_volume\" interval={} N:{}".format(hostname,interval,watchman_volume))
#          l.release()
          sys.stdout.flush()

finally:
    p.terminate()
