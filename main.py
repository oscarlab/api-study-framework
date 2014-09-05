#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen

import os
import sys
import re
import time
from datetime import datetime

# Example
def print_any(args):
	time.sleep(args[0])
	print args[1]

def main():
	jmgr = JobManager()
	wmgr = WorkerManager(jmgr, 4)

	# Example
	jmgr.add_job("Say hello", print_any, (3, "Hello",))

	while True:
		try:
			wmgr.join()
		except KeyboardInterrupt:
			if make_screen(jmgr, wmgr):
				wmgr.exit()
				return

if __name__ == "__main__":
	startTime = datetime.now()
	main()
	print "Workers Up Time:", datetime.now() - startTime
