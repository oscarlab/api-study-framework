#!/usr/bin/python
import subprocess
import sys
binaryname = sys.argv[1]
pattern1 = "syscall"
pattern2 = "sysenter"
pattern3 = "int 0x80"
process1 = subprocess.Popen(["objdump", "-d", binaryname],
                             stdout=subprocess.PIPE
                           )
process2 = subprocess.Popen(["grep", "-e" , pattern1 , "-e" , pattern2 , "-e" , pattern3],
			stdin=process1.stdout,
			stdout=subprocess.PIPE,stderr=subprocess.PIPE)
process1.stdout.close();
stdout_list = process2.communicate()[0]
if stdout_list:
	print "System call made"
else:
	print "System call not made"


