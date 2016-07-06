#!/usr/bin/python

from ui import make_screen
from task import Task, tasks
from os_target import OS
from sql import SQL
from scheduler import Scheduler, SimpleScheduler
from utils import get_config

import package
import binary
import symbol
import callgraph

import sys
import os

if __name__ == "__main__":
	foreground = True
	nworkers = 0

	i = 1
	while i < len(sys.argv):
		if sys.argv[i] == "-help":
			print "./start-framework [-help] [-background] [-worker <nworker>]"
			os._exit(0)
		elif sys.argv[i] == "-background":
			foreground = False
		elif sys.argv[i] == "-worker":
			i += 1
			if i < len(sys.argv):
				nworkers = int(sys.argv[i])
		i += 1

	os_target = OS.get_target(get_config('os_target'))
	sql = SQL.get_engine(get_config('sql_engine'))
	scheduler = Scheduler.get_scheduler(get_config('scheduler', "scheduler.SimpleScheduler"), os_target, sql)

	for i in range(nworkers):
		scheduler.add_worker()

	sorted_tasks = []
	for _, task in sorted(tasks.items(), key = lambda item: (item[1].order, item[0])):
		sorted_tasks.append(task)

	if foreground:
		make_screen(scheduler, sorted_tasks)

	os._exit(0)
