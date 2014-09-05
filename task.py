#!/usr/bin/python

import os
import sys
import re
import time

class Task:
	@classmethod
	def run(cls, args):
		return

	@classmethod
	def gen_name(cls, args):
		return ""

	@classmethod
	def create_job(cls, jmgr, args):
		jmgr.add_job(cls.gen_name(args), cls.run, args)

all_tasks = []

# Example
class ExampleTask(Task):
	name = "Example - Say Hello"
	nargs = 2
	@classmethod
	def run(cls, args):
		time.sleep(args[0])
		print args[1]

	@classmethod
	def gen_name(cls, args):
		return "Say hello"
