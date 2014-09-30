#!/usr/bin/python

import os
import fnmatch
import sys
import re
import shutil
import signal
from datetime import datetime
from multiprocessing import Process, Queue, JoinableQueue, Value, current_process
from Queue import Empty
from threading import Thread, Lock, Event
import time
import traceback

job_id_gen = Value('I', 1)
def get_job_id():
	id = job_id_gen.value
	job_id_gen.value += 1
	return id

class Job(object):
	def __init__(self, id, name, func, args):
		self.id = id
		self.name = name
		self.func = func
		self.args = args

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

class QueueReceiver(Thread):
	def __init__(self, lock, exit_event):
		Thread.__init__(self)
		self.queue = Queue()
		self.list = []
		self.lock = lock
		self.exit_event = exit_event

	def receive(self, block=True):
		while True:
			local_list = []
			if block:
				try:
					o = self.queue.get(True, 1)
					local_list.append(o)
					time.sleep(0)
				except Empty:
					return
			while True:
				try:
					o = self.queue.get(False)
					local_list.append(o)
					time.sleep(0)
				except Empty:
					break
			if local_list:
				self.lock.acquire()
				self.list += local_list
				self.lock.release()

	def run(self):
		while not self.exit_event.is_set():
			self.receive()

class JobManager:
	def __init__(self):
		self.work_queue = JoinableQueue()
		self.master_process = current_process()
		self.exit_event = Event()
		self.lock = Lock()
		self.work_receiver = QueueReceiver(self.lock, self.exit_event)
		self.done_receiver = QueueReceiver(self.lock, self.exit_event)
		self.work_receiver.start()
		self.done_receiver.start()

	def exit(self):
		print "joining threads..."
		self.exit_event.set()
		self.work_receiver.join()
		self.done_receiver.join()

	def update_queue(self):
		self.work_receiver.receive(False)
		self.done_receiver.receive(False)

	def get_jobs(self):
		jobs = []
		self.lock.acquire()
		for j in self.work_receiver.list:
			s = None
			if j in self.done_receiver.list:
				s = next(s for s in self.done_receiver.list if s == j)
			jobs.append((j.id, j.name, s))
		self.lock.release()
		return jobs

	def add_job(self, name, func, args):
		j = Job(get_job_id(), name, func, args)
		self.work_queue.put(j)
		if current_process() == self.master_process:
			self.lock.acquire()
			self.work_receiver.list.append(j)
			self.lock.release()
		else:
			self.work_receiver.queue.put(Job(j.id, name, func, args))

	def requeue_job(self, id):
		job = None
		self.lock.acquire()
		try:
			job = next(j for j in self.work_receiver.list if j.id == id)
		except:
			pass
		self.lock.release()
		if job:
			self.add_job(job.name, job.func, job.args)

	def clear_finished_jobs(self):
		self.lock.acquire()
		done_jobs = [s for s in self.done_receiver.list if s in self.work_receiver.list and s.success]
		self.work_receiver.list = [j for j in self.work_receiver.list if j not in done_jobs]
		self.done_receiver.list = [s for s in self.done_receiver.list if s not in done_jobs]
		self.lock.release()

class Worker(Process):
	def __init__(self, job_manager, sql):
		Process.__init__(self)
		self.job_manager = job_manager
		self.sql = sql
		self.current_job = Value('I', 0)

	def run(self):
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		current = current_process()
		print "Worker start running:", current.name
		logfile = current.name + ".log"
		if os.path.exists(logfile):
			os.system('cat ' + logfile + ' >> ' + logfile + '.bak')
		log = os.open(logfile, os.O_RDWR|os.O_CREAT|os.O_TRUNC)
		os.dup2(log, 1)
		os.dup2(log, 2)

		self.sql.connect()

		while True:
			j = self.job_manager.work_queue.get()
			if not j:
				self.work_queue.task_done()
				break
			self.current_job.value = j.id
			s = JobStatus(j.id, j.name)
			print "Start Job:", j.name, s.start_time
			try:
				j.run(self.job_manager, self.sql)
			except Exception as err:
				print err.__class__.__name__, ':', err
				print 'Traceback:'
				traceback.print_tb(sys.exc_info()[2])
				s.success = False
			s.end_time = datetime.now()
			print "Finish Job:", j.name, s.end_time
			self.current_job.value = 0
			self.job_manager.work_queue.task_done()
			self.job_manager.done_receiver.queue.put(s)

		self.sql.disconnect()

class WorkerManager:
	def __init__(self, jmgr, sql, nworkers=0):
		self.workers = []
		self.job_manager = jmgr
		self.sql = sql
		for i in range(nworkers):
			self.add_worker()

	def add_worker(self):
		w = Worker(self.job_manager, self.sql)
		w.start()
		self.workers.append(w)

	def get_workers(self):
		return [(w.name, w.current_job.value) for w in self.workers if
				w.is_alive()]

	def join(self):
		for w in self.workers:
			w.join()

	def exit(self):
		print "Terminating workers..."
		for w in self.workers:
			w.terminate()
