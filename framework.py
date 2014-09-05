#!/usr/bin/python

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

	def __eq__(self, obj):
		return self.id == obj.id

	def run(self):
		self.func(self.args)

class JobStatus(object):
	def __init__(self, id, name, func, args):
		self.id = id
		self.name = name
		self.func = func
		self.args = args
		self.start_time = datetime.now()

	def __eq__(self, obj):
		return self.id == obj.id

class JobManager:
	def __init__(self):
		self.work_queue = JoinableQueue()
		self.done_queue = Queue()
		self.jobs = []
		self.done_jobs = []

	def update_queue(self):
		while not self.done_queue.empty():
			s = self.done_queue.get(block = False)
			self.done_jobs.append(s)

	def get_jobs(self):
		self.update_queue()
		return [(j.id, j.name, j in self.done_jobs) for j in self.jobs]

	def add_job(self, name, func, args):
		j = Job(name, func, args)
		self.jobs.append(j)
		self.work_queue.put(j)

class Worker(Process):
	def __init__(self, work_queue, done_queue):
		Process.__init__(self)
		self.work_queue = work_queue
		self.done_queue = done_queue
		self.current_job = Value('I', 0)

	def run(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		current = current_process()
		print "Worker start running:", current.name

		while True:
			j = self.work_queue.get()
			if not j:
				self.work_queue.task_done()
				break
			self.current_job.value = j.id
			s = JobStatus(j.id, j.name, j.func, j.args)
			j.run()
			s.end_time = datetime.now()
			self.current_job.value = 0
			self.work_queue.task_done()
			self.done_queue.put(s)

class WorkerManager:
	def __init__(self, jmgr, nworkers=0):
		self.workers = []
		self.job_manager = jmgr
		for i in range(nworkers):
			self.add_worker()

	def add_worker(self):
		w = Worker(self.job_manager.work_queue, self.job_manager.done_queue)
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
