#!/usr/bin/python

import os
import fnmatch
import sys
import subprocess
import re
import shutil
from datetime import datetime
from multiprocessing import Process, Queue, JoinableQueue, current_process
import multiprocessing

class Job(object):
	id_gen = 0
	@classmethod
	def get_id(cls):
		cls.id_gen = cls.id_gen + 1
		return cls.id_gen

	def __init__(self, name, func, args):
		self.name = name
		self.func = func
		self.args = args
		self.id = Job.get_id()
		self.done = False

	def __eq__(self, obj):
		return self.id == obj.id

	def run(self):
		self.func(self.args)

class JobManager:
	def __init__(self):
		self.work_queue = JoinableQueue()
		self.done_queue = Queue()
		self.jobs = []
		self.done_jobs = []

	def update_queue(self):
		try:
			j = self.done_queue.get(block = False)
			while j:
				self.done_jobs.append(j)
				j = self.done_queue.get(block = False)
		except:
			return

	def get_jobs(self):
		self.update_queue()
		return [(j.id, j.name, j in self.done_jobs) for j in self.jobs]

	def add_job(self, name, func, args):
		j = Job(name, func, args)
		self.jobs.append(j)
		self.work_queue.put(j)

def worker(work_queue, done_queue):
	current = current_process()
	print "Worker start running:", current.name

	try:
		j = work_queue.get()
		while j:
			j.run()
			work_queue.task_done()
			done_queue.put(j)
			j = work_queue.get()
	except KeyboardInterrupt:
		return

class WorkerManager:
	def __init__(self, jmgr, nworkers=0):
		self.workers = []
		self.job_manager = jmgr
		for i in range(nworkers):
			self.add_worker()

	def add_worker(self):
		p = Process(target=worker, args=(self.job_manager.work_queue,
			self.job_manager.done_queue,))
		p.start()
		self.workers.append(p)

	def join(self):
		for p in self.workers:
			p.join()
			self.workers.remove(p)
			del p

	def exit(self):
		for p in self.workers:
			p.terminate()
			self.workers.remove(p)
			del p
