#!/usr/bin/python

from framework import JobManager, WorkerManager
from ui import make_screen
from task import tasks, Task
from os_target import OS
import os_target
import package
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
	os_target = OS.get_target(get_config('os_target'))
	sql = SQL.get_engine(get_config('sql_engine'))

	if not os_target:
		print "os_target must be defined in config.py"
		return

	if not sql:
		print "sql_engine must be defined in config.py"
		return

	for task_name in sorted(tasks.keys()):
		Task.register(tasks[task_name])

	ncpu = multiprocessing.cpu_count() - 1;
	if ncpu == 0:
		ncpu = 1
	jmgr = JobManager()
	wmgr = WorkerManager(jmgr, os_target, sql, ncpu)

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
