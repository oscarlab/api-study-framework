#!/usr/bin/python

import os
import sys
import re

class Task:
	registered_tasks = []
	@classmethod
	def register(cls, task):
		Task.registered_tasks.append(task)

	def __init__(self, name, func, arg_defs = [], job_name = None):
		self.name = name
		self.func = func
		self.arg_defs = arg_defs
		self.job_name = job_name

	def create_job(self, jmgr, args):
		if self.job_name:
			job_name = self.job_name(args)
		else:
			job_name = self.name
		jmgr.add_job(job_name, self.func, args)

tasks = dict()
subtasks = dict()
