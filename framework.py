#!/usr/bin/python

from sql import SQLite

import os
import fnmatch
import sys
import subprocess
import re
import shutil
import signal
from datetime import datetime
from multiprocessing import Process, Queue, JoinableQueue, Value, current_process
import multiprocessing
import traceback

job_id_gen = Value('I', 1)
def get_job_id():
	id = job_id_gen.value
	job_id_gen.value += 1
	return id

class Job(object):
	def __init__(self, id, name, func, args):
		self.name = name
		self.func = func
		self.args = args
		self.id = id

	def __eq__(self, obj):
		return self.id == obj.id

	def run(self, jmgr, sql):
		self.func(jmgr, sql, self.args)

class JobStatus(object):
	def __init__(self, id, name):
		self.id = id
		self.name = name
		self.start_time = datetime.now()
		self.success = True

	def __eq__(self, obj):
		return self.id == obj.id

class JobManager:
	def __init__(self):
		self.work_queue = JoinableQueue()
		self.done_queue = Queue()
		self.more_queue = Queue()
		self.jobs = []
		self.done_jobs = []
		self.master_process = current_process()

	def update_queue(self):
		while not self.done_queue.empty():
			s = self.done_queue.get(block = False)
			if not s:
				break
			if s.success:
				self.done_jobs.append(s)

		while not self.more_queue.empty():
			j = self.more_queue.get(block = False)
			if not j:
				break
			self.jobs.append(j)

	def get_jobs(self):
		self.update_queue()
		return [(j.id, j.name, j in self.done_jobs) for j in self.jobs]

	def add_job(self, name, func, args):
		j = Job(get_job_id(), name, func, args)
		self.work_queue.put(j)
		if current_process() == self.master_process:
			self.jobs.append(j)
		else:
			self.more_queue.put(Job(j.id, name, func, args))

	def clear_finished_jobs(self):
		for j in self.jobs:
			if j in self.done_jobs:
				self.jobs.remove(j)
				self.done_jobs.remove(j)

class Worker(Process):
	def __init__(self, job_manager):
		Process.__init__(self)
		self.job_manager = job_manager
		self.current_job = Value('I', 0)

	def run(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		current = current_process()
		print "Worker start running:", current.name

		log = os.open(current.name + ".log",
				os.O_RDWR|os.O_CREAT|os.O_TRUNC)
		os.dup2(log, 1)
		os.dup2(log, 2)

		sql = SQLite()

		while True:
			j = self.job_manager.work_queue.get()
			if not j:
				self.work_queue.task_done()
				break
			self.current_job.value = j.id
			s = JobStatus(j.id, j.name)
			print "Start Job:", j.name, s.start_time
			try:
				j.run(self.job_manager, sql)
			except Exception as err:
				print err.__class__.__name__, ':', err
				print 'Traceback:'
				traceback.print_tb(sys.exc_info()[2])
				s.success = False
			s.end_time = datetime.now()
			print "Finish Job:", j.name, s.end_time
			self.current_job.value = 0
			self.job_manager.work_queue.task_done()
			self.job_manager.done_queue.put(s)

		del sql

class WorkerManager:
	def __init__(self, jmgr, nworkers=0):
		self.workers = []
		self.job_manager = jmgr
		for i in range(nworkers):
			self.add_worker()

	def add_worker(self):
		w = Worker(self.job_manager)
		w.start()
		self.workers.append(w)

	def get_workers(self):
		return [(w.name, w.current_job.value) for w in self.workers if
				w.is_alive()]

	def join(self):
		for w in self.workers:
			w.join()

	def exit(self):
		for w in self.workers:
			w.terminate()
