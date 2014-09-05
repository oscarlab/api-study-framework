#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen

import os
import sys
import re
from datetime import datetime

# Example
def print_any(args):
	print args

def main():
	jmgr = JobManager()
	wmgr = WorkerManager(jmgr, 4)

	# Example
	jmgr.add_job("Say hello", print_any, ("Hello",))

	cont = True
	while cont:
		try:
			wmgr.join()
		except KeyboardInterrupt:
			if make_screen(jmgr, wmgr):
				cont = False

	wmgr.exit()

if __name__ == "__main__":
	startTime = datetime.now()
	main()
	print "Workers Up Time:", datetime.now() - startTime
