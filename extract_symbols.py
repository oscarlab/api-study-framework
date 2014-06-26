#!/usr/bin/python
import subprocess
import sys
import re
binaryname = sys.argv[1]
process1 = subprocess.Popen(["readelf", "-a", binaryname],
                             stdout=subprocess.PIPE
                           )
count = 0
str = "example write rread readif read@pit"
str1 =  process1.communicate()[0] 
#print str1
with open("listfile.txt") as f:
    for line in f:
	match = re.search("\\b"+line.strip()+"\\b",str1)
	if match:
	   print match.group()
           count = count + 1
print "Total number of syscalls made out of 1523:" ,count
