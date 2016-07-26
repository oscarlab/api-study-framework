#!/usr/bin/python

from utils import get_config, root_dir

import os
import sys
import socket
import logging
from multiprocessing import Process, Queue, Value, Event, current_process
from multiprocessing.managers import SyncManager, ValueProxy
from Queue import Empty
from threading import Thread
from datetime import datetime
import traceback
import inspect
import importlib
import random

class Scheduler:
	def __init__(self, os_target, sql):
		self.os_target = os_target
		self.sql = sql
		return

	@classmethod
	def get_scheduler(cls, name, os_target, sql):
		names = name.split('.')
		obj = importlib.import_module(names[0])
		for n in names[1:]:
			next = None
			for (key, val) in inspect.getmembers(obj):
				if n == key:
					next = val
					break
			if not next:
				raise Exception('Object ' + name + ' is not found')
			obj = next
		if not inspect.isclass(obj):
			raise Exception('Object ' + name + ' is not a class')
		if not issubclass(obj, Scheduler):
			raise Exception('Object ' + name + ' is not a subclass of Scheduler')
		return obj(os_target, sql)

default_scheduler_host = '127.0.0.1'
default_scheduler_port = 5000

class Job:
	def __init__(self, name, func, args):
		self.id = None
		self.name = name
		self.func = func
		self.args = args
		self.status = None

	def __eq__(self, obj):
		return self.id == obj.id

	def run(self, jmgr, os_target, sql):
		self.func(jmgr, os_target, sql, self.args)
	
	def get_name(self):
		return self.name

class JobStatus:
	def __init__(self, id):
		self.id = id
		self.start_time = datetime.now()
		self.success = True

	def __eq__(self, obj):
		return self.id == obj.id

class WorkerProcess(Process):
	def __init__(self, scheduler, logfile):
		Process.__init__(self)
		self.scheduler = scheduler
		self.logfile = logfile

	def run(self):
		if os.path.exists(self.logfile):
			os.system('cat ' + self.logfile + ' >> ' + self.logfile + '.bak')
		log = os.open(self.logfile, os.O_RDWR|os.O_CREAT|os.O_TRUNC)
		os.dup2(log, 1)
		os.dup2(log, 2)
		logging.info("Hello from the Worker Theread")
		self.scheduler.sql.connect()
		logging.info("Connected to the scheduler")
		while True:
			try:
				logging.info("Worker checking queue")
				j = self.scheduler.worker_queue.get()
				logging.info("Worker found the following task:"+j.get_name())
			except Empty:
				logging.info("Worker found the queue empty")
				continue

			self.scheduler.workers.update([(self.name, j.id)])
			s = JobStatus(j.id)
			logging.info("Start Job: " + j.name + " " + str(s.start_time))
			try:
				j.run(self.scheduler, self.scheduler.os_target, self.scheduler.sql)
			except Exception as err:
				logging.error(err.__class__.__name__ + ' : ' + str(err))
				logging.error('Traceback:')
				traceback.print_tb(sys.exc_info()[2])
				s.success = False
			s.end_time = datetime.now()
			logging.info("Finish Job: " + j.name + " " + str(s.end_time))
			self.scheduler.workers.update([(self.name, 0)])

			self.scheduler.status_queue.put(s)

class SchedulerProcess(Process):
	def __init__(self, scheduler, server):
		Process.__init__(self)
		self.scheduler = scheduler
		self.server = server

	def run(self):
		def receive_submission(scheduler):
			while True:
				jobs = []
				timeout = None
				while True:
					try:
						o = scheduler.submit_queue.get(timeout is None, timeout)
#						logging.info("Recieved a job "+str(o.get_name()))
						jobs.append(o)
						timeout = 0
					except Empty:
						break

				for j in jobs:
					j.id = scheduler.job_counter.value
					scheduler.job_counter.value += 1
					scheduler.jobs.update([(j.id, j)])
					scheduler.worker_queue.put(j)

		def receive_status(scheduler):
			while not scheduler.exit_event.is_set():
				replies = []
				timeout = None
				while True:
					try:
						o = scheduler.status_queue.get(timeout is None, timeout)
						replies.append(o)
						timeout = 0
					except Empty:
						break

				for s in replies:
					if s.id in scheduler.jobs:
						try:
							j = scheduler.jobs.get(s.id)
						except KeyError:
							continue
						j.status = s
						scheduler.jobs.update([(s.id, j)])

		logging.info("Scheduler process started.")

		Thread(target=receive_submission, args=(self.scheduler,)).start()
		Thread(target=receive_status, args=(self.scheduler,)).start()
		self.server.serve_forever()

class HostProcess(Process):
	def __init__(self, scheduler, host_server, host_server_name):
		Process.__init__(self)
		self.scheduler = scheduler
		self.host_server = host_server
		self.host_server_name = host_server_name
		self.worker_count = 0

	def run(self):
		self.scheduler.job_counter = Value('I', 1)
		self.scheduler.jobs = dict()
		self.scheduler.submit_queue = Queue()
		self.scheduler.worker_queue = Queue()
		self.scheduler.status_queue = Queue()
		self.scheduler.exit_event = Event()
		self.scheduler.workers = dict()

		self.scheduler_process = None
		scheduler_server = None
		try:
			class SyncManagerScheduler(SyncManager):
				pass

			SyncManagerScheduler.register('get_jobs', callable=lambda: self.scheduler.jobs)
			SyncManagerScheduler.register('get_submit_queue', callable=lambda: self.scheduler.submit_queue)
			SyncManagerScheduler.register('get_worker_queue', callable=lambda: self.scheduler.worker_queue)
			SyncManagerScheduler.register('get_status_queue', callable=lambda: self.scheduler.status_queue)
			SyncManagerScheduler.register('get_exit_event', callable=lambda: self.scheduler.exit_event)
			SyncManagerScheduler.register('get_workers', callable=lambda: self.scheduler.workers)

			scheduler_server = SyncManagerScheduler(
					address=(self.scheduler.scheduler_host, self.scheduler.scheduler_port),
				).get_server()

			logging.info("Scheduler listening at \"" + self.scheduler.scheduler_host + ":" + str(self.scheduler.scheduler_port) + "\".")
		except socket.error:
			logging.info("Not scheduler server.")
			pass

		if scheduler_server:
			self.scheduler_process = SchedulerProcess(self.scheduler, scheduler_server)
			self.scheduler_process.start()

		try:
			self.scheduler.connect()
		except socket.error:
			logging.error("Failed connecting to the scheduler.")
			self.host_server.listener.close()
			os._exit(0)

		self.worker_processes = []

		def receive_connection(server):
			server.serve_forever()

		Thread(target=receive_connection, args=(self.host_server,)).start()

		self.scheduler.exit_event.wait()

		if self.scheduler_process:
			logging.info("Terminating scheduler process")
			self.scheduler_process.terminate()

		for w in self.worker_processes:
			logging.info("Terminating worker process " + w.name)
			w.terminate()

		host_file = root_dir + '/localserver.port'
		if os.path.exists(host_file):
			os.unlink(host_file)

		self.host_server.listener.close()
		os._exit(0)

	def add_worker(self):
		self.worker_count += 1
		w = WorkerProcess(self.scheduler, 'Worker-' + str(self.worker_count) + '.log')
		w.name = self.host_server_name + '-' + str(self.worker_count)
		w.start()
		self.worker_processes.append(w)
		self.scheduler.workers.update([(w.name, 0)])

class SimpleScheduler(Scheduler):
	def __init__(self, os_target, sql):
		Scheduler.__init__(self, os_target, sql)

		current_process().authkey = 'SimpleScheduler'

		self.scheduler_host = get_config('scheduler_host', default_scheduler_host)
		self.scheduler_port = get_config('scheduler_port', default_scheduler_port)
		self.connected = False

		host_file = root_dir + '/localserver.port'
		host_port = None
		if os.path.exists(host_file):
			with open(host_file, 'r') as f:
				host_port = int(f.read())
		localhost = '127.0.0.1'
		self.host_client = None
	
		while self.host_client is None:
			if host_port is None:
				host_port = random.randint(50001,50030)
				with open(host_file, 'w') as f:
					f.write(str(host_port))

			host_server = None
			try:
				class SyncManagerHost(SyncManager):
					pass

				def add_worker():
					if self.host_process:
						self.host_process.add_worker()
					return True

				SyncManagerHost.register('get_root', callable=lambda: root_dir)
				SyncManagerHost.register('add_worker', callable=add_worker)

				host_server = SyncManagerHost(
						address=(localhost, host_port),
					).get_server()

				logging.info("Host listening at \"" + localhost + ":" + str(host_port) + "\".")
			except socket.error:
				pass

			if host_server:
				self.host_process = None
				child = os.fork()
				if child == 0:
					os.setsid()
					self.host_process = HostProcess(self, host_server, socket.gethostname() + ':' + str(host_port))
					self.host_process.start()
					os._exit(0)
				else:
					os.waitpid(child, 0)
					host_server.listener.close()

			try:
				class SyncManagerInterface(SyncManager):
					pass

				SyncManagerInterface.register('get_root')
				SyncManagerInterface.register('add_worker')

				self.host_client = SyncManagerInterface(
						address=(localhost, host_port),
					)
				self.host_client.connect()
			except:
				if host_server:
					logging.error("Failed initializing the host.")
					os._exit(0)
				host_port = None
				self.host_client = None

			if self.host_client and self.host_client.get_root() == root_dir:
				break

	def connect(self):
		if self.connected:
			return

		class SyncManagerClient(SyncManager):
			pass

		logging.info("Connecting to Scheduler (may take a few seconds)...")

		SyncManagerClient.register('get_jobs')
		SyncManagerClient.register('get_submit_queue')
		SyncManagerClient.register('get_worker_queue')
		SyncManagerClient.register('get_status_queue')
		SyncManagerClient.register('get_exit_event')
		SyncManagerClient.register('get_workers')

		client = SyncManagerClient(
				address=(self.scheduler_host, self.scheduler_port),
			)
		client.connect()

		self.jobs = client.get_jobs()
		self.submit_queue = client.get_submit_queue()
		self.worker_queue = client.get_worker_queue()
		self.status_queue = client.get_status_queue()
		self.exit_event = client.get_exit_event()
		self.workers = client.get_workers()

		logging.info("Connected to the scheduler: " + self.scheduler_host + ":" + str(self.scheduler_port))
		self.connected = True

	def add_worker(self):
		self.host_client.add_worker()

	def get_workers(self):
		self.connect()
		return sorted(self.workers.items(), key=lambda w: w[0])

	def add_job(self, name, func, args):
		self.connect()
		j = Job(name, func, args)
		logging.info("Adding job to submit queue: " + j.get_name())
		self.submit_queue.put(j)

	def requeue_job(self, id):
		self.connect()
		if self.jobs.has_key(id):
			j = self.jobs.get(id)
			self.add_job(j.name, j.func, j.args)

	def get_jobs(self):
		self.connect()
		return [(j.id, j.name, j.status) for j in sorted(self.jobs.values(), key=lambda j: j.id)]

	def clear_jobs(self):
		self.connect()
		for j in self.jobs.values():
			if j.status is not None and j.status.success:
				try:
					self.jobs.pop(j.id)
				except KeyError:
					pass
	
	def requeue_failed_jobs(self):
		self.connect()
		i = 0
		for (id, _, _) in self.get_failed_jobs():
			self.requeue_job(id)
			i=i+1
		return i
	
	def get_failed_jobs(self):
		self.connect()
		failed_jobs = []
		for j in self.jobs.values():
			if j.status is not None and j.status.success is False:
				failed_jobs.append((j.id, j.name, j.status))
		return failed_jobs

	def clear_failed_jobs(self):
		self.connect()
		for j in self.jobs.values():
			if j.status is not None and j.status.success is False:
				try:
					self.jobs.pop(j.id)
				except KeyError:
					pass

	def print_failed_jobs(self):
		self.connect()
		logging.info("Failed Jobs:")
		for (id,name,_) in self.get_failed_jobs():
			logging.info(str(id) + name)

	def exit(self):
		self.connect()
		self.exit_event.set()
