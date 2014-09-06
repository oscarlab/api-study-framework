#!/usr/bin/python

from task import Task

import os
import sys
import re
import time

def ExampleTask_run(jmgr, args):
	time.sleep(int(args[0]))
	print args[1]

def ExampleTask_job_name(args):
	return "Say hello"

ExampleTask = Task(
	name="Example - Say Hello",
	func=ExampleTask_run,
	arg_defs=["Sleep Time", "Print-out String"],
	job_name=ExampleTask_job_name)

def ExampleMoreTask_run(jmgr, args):
	for i in range(int(args[0])):
		ExampleTask.create_job(jmgr, args[1:])

def ExampleMoreTask_job_name(args):
	return "Say hello More"

ExampleMoreTask = Task(
	name="Example - Say Hello More",
	func=ExampleMoreTask_run,
	arg_defs=["Num of Jobs", "Sleep Time", "Print-out String"],
	job_name=ExampleMoreTask_job_name)
