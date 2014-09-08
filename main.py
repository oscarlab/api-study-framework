#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen
from task import Task
# from example import ExampleTask, ExampleMoreTask
from package import PackageListByNames, PackageListByPrefixes, PackageListByRanks
from package_popularity import PackagePopularity

import os
import sys
import re
from datetime import datetime
import multiprocessing

def main():
	# Task.register(ExampleTask)
	# Task.register(ExampleMoreTask)
	Task.register(PackageListByNames)
	Task.register(PackageListByPrefixes)
	Task.register(PackageListByRanks)
	Task.register(PackagePopularity)

	jmgr = JobManager()
	wmgr = WorkerManager(jmgr, multiprocessing.cpu_count())

	while True:
		try:
			wmgr.join()
		except KeyboardInterrupt:
			if make_screen(jmgr, wmgr, Task.registered_tasks):
				wmgr.exit()
				return

if __name__ == "__main__":
	startTime = datetime.now()
	main()
	print "Workers Up Time:", datetime.now() - startTime
