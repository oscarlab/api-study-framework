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

	def run(self, jmgr):
		self.func(jmgr, self.args)

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
		self.more_queue = Queue()
		self.jobs = []
		self.done_jobs = []
		self.master_process = current_process()

	def update_queue(self):
		while not self.done_queue.empty():
			s = self.done_queue.get(block = False)
			if not s:
				break
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

class Worker(Process):
	def __init__(self, job_manager):
		Process.__init__(self)
		self.job_manager = job_manager
		self.current_job = Value('I', 0)

	def run(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		current = current_process()
		print "Worker start running:", current.name

		while True:
			j = self.job_manager.work_queue.get()
			if not j:
				self.work_queue.task_done()
				break
			self.current_job.value = j.id
			s = JobStatus(j.id, j.name, j.func, j.args)
			j.run(self.job_manager)
			s.end_time = datetime.now()
			self.current_job.value = 0
			self.job_manager.work_queue.task_done()
			self.job_manager.done_queue.put(s)

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
