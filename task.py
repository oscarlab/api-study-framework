#!/usr/bin/python

import os
import sys
import re

class Task:
	registered_tasks = []
	@classmethod
	def register(cls, task):
		Task.registered_tasks.append(task)

	def __init__(self, name, func, arg_defs, job_name):
		self.name = name
		self.func = func
		self.arg_defs = arg_defs
		self.job_name = job_name

	def create_job(self, jmgr, args):
		jmgr.add_job(self.job_name(args), self.func, args)

tasks = dict()
subtasks = dict()
