#!/usr/bin/python

import subprocess
import sys
import re
import time
from socket import gethostname
import math
import thread

rtl_433_cmd = "/usr/local/bin/rtl_433 -l 0 -R 42"

# windows
#rtl_433_cmd = r"x:\path\to\rtl_433.exe -l0 -R42"

hostname = gethostname()

watchman_level = "U"
watchman_temperature = "U"
watchman_volume = "U"
watchman_pct = "U"
# kerosene
expansion_coeff = 0.00099
# tank height in cm
tank_height = 115
# tank capacity in litres
tank_capacity = 1000
# 1 = rectangle, 2 = sphere
tank_shape = 1

#To adjust for fluid expansion
#Report volume/percentage as they would be at 10 C
canon_temp = 10

# 2016-01-11 19:42:37 Oil Watchman 860771e 80 26 5.000000 0 49

watchman_id = "860771e"

watchman_re = re.compile(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d Oil Watchman ' + watchman_id + ' ')
watchman_data_re = re.compile(r'([-+]?[0-9]*\.?[0-9]+.) \d+ (\d+)$')

interval = 10
elapsed = 0

def watch_rtl433():
    for line in iter(p.stdout.readline, b''):
    	if watchman_re.match(line) is not None:
    	    watchman_data = watchman_data_re.search(line)
    	    if watchman_data is not None:
		global watchman_level
		global watchman_temperature
		global watchman_volume
		global watchman_pct
		watchman_level = watchman_data.group(2)
		watchman_temperature = watchman_data.group(1)
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

p = subprocess.Popen(rtl_433_cmd.split(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
thread.start_new_thread(watch_rtl433,())

try:
    while True:
       time.sleep(1)
       if p.poll() is not None:
          break
       elapsed += 1
       if elapsed % interval == 0:
#          print "PUTVAL \"%s/exec-watchman/gauge-oil_level\" interval=%d N:%s" % (hostname,interval,watchman_level)
          print "PUTVAL \"%s/exec-watchman/oiltank_temperature-oil_temperature\" interval=%d N:%s" % (hostname,interval,watchman_temperature)
          print "PUTVAL \"%s/exec-watchman/oiltank_pct-oil_percent\" interval=%d N:%s" % (hostname,interval,watchman_pct)
          print "PUTVAL \"%s/exec-watchman/oiltank_volume-oil_volume\" interval=%d N:%s" % (hostname,interval,watchman_volume)
    	  sys.stdout.flush()

finally:
    p.terminate()

