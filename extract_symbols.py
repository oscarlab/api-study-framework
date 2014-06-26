#!/usr/bin/python
import subprocess
import sys
import re
binaryname = sys.argv[1]
process = subprocess.Popen(["readelf", "--dyn-syms", binaryname],
                             stdout=subprocess.PIPE
                           )
count = 0
#str =  process.communicate()[0] 
for line in process.stdout:
	parts = line.split()
#	print len(parts)
	if len(parts) > 7:
		if parts[3] == 'FUNC' and (parts[4] == 'GLOBAL' or parts[4] == 'WEAK'):
			count = count + 1
 			f = parts[7].split("@")[0]
			print f
print "Total number of functions in " + binaryname + " are " , count

