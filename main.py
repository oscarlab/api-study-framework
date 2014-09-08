#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen
from task import Task
# from example import ExampleTask, ExampleMoreTask
import package
import package_popularity

import os
import sys
import re
from datetime import datetime
import multiprocessing

def main():
	# Task.register(ExampleTask)
	# Task.register(ExampleMoreTask)
	Task.register(package.PackageListByNames)
	Task.register(package.PackageListByPrefixes)
	Task.register(package.PackageListByRanks)
	Task.register(package.PackageListByRanks)
	Task.register(package.PackageUnpack)
	Task.register(package.BinaryListByNames)
	Task.register(package.BinaryListByPrefixes)
	Task.register(package.BinaryListByRanks)
	Task.register(package_popularity.PackagePopularity)

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
