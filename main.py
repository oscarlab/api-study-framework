#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen
from task import Task
# from example import ExampleTask, ExampleMoreTask
import package
import package_popularity
import symbol
import callgraph
import syscall
from sql import SQL

import os
import sys
import re
from datetime import datetime
import multiprocessing
import importlib

config = None
def get_config(key, default=None):
	global config
	if config is None:
		try:
			config_module = importlib.import_module('config')
			config = config_module.config
		except ImportError:
			config = {}

	if key in config:
		return config[key]
	return default

temp_dir = None
def get_temp_dir():
	global temp_dir
	if not temp_dir:
		temp_dir = get_config('temp_dir', '/tmp/syspop-' + str(os.getuid()))
		try:
			os.mkdir(temp_dir)
			print "Create temp dir:", temp_dir
		except OSError:
			pass
	return temp_dir

def main():
	# Task.register(ExampleTask)
	# Task.register(ExampleMoreTask)
	Task.register(package.PackageListByNames)
	Task.register(package.PackageListByPrefixes)
	Task.register(package.PackageListByRanks)
	Task.register(package.PackageUnpack)
	Task.register(package.BinaryListByNames)
	Task.register(package.BinaryListByPrefixes)
	Task.register(package.BinaryListByRanks)
	Task.register(symbol.BinaryInfoByNames)
	Task.register(symbol.BinaryInfoByPrefixes)
	Task.register(symbol.BinaryInfoByRanks)
	Task.register(callgraph.BinaryCallgraph)
	Task.register(callgraph.BinaryCallInfoByNames)
	Task.register(callgraph.BinaryCallInfoByPrefixes)
	Task.register(callgraph.BinaryCallInfoByRanks)
	Task.register(package_popularity.PackagePopularity)
	Task.register(syscall.ListSyscall)

	package.update_apt(get_config('package_source'))
	sql = SQL.get_engine(get_config('sql_engine', 'postgresql.PostgreSQL'))

	ncpu = multiprocessing.cpu_count() - 1;
	if ncpu == 0:
		ncpu = 1
	jmgr = JobManager()
	wmgr = WorkerManager(jmgr, sql, ncpu)

	while True:
		try:
			wmgr.join()
		except KeyboardInterrupt:
			if make_screen(jmgr, wmgr, Task.registered_tasks):
				wmgr.exit()
				jmgr.exit()
				return

root_dir = os.getcwd()
null_dev = open(os.devnull, 'w')

if __name__ == "__main__":
	startTime = datetime.now()
	main()
	print "Workers Up Time:", datetime.now() - startTime
