#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen

import os
import sys
import re
from datetime import datetime

def main():
	jmgr = JobManager()
	wmgr = WorkerManager(jmgr, 4)

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
