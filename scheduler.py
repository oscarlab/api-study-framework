#!/usr/bin/python

from utils import get_config, root_dir

import os
import sys
import socket
from multiprocessing import Process, Queue, Value, Event, current_process
from multiprocessing.managers import SyncManager
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
default_scheduler_auth = 'api-compat-study'

class Job:
	def __init__(self, id, name, func, args):
		self.id = id
		self.name = name
		self.func = func
		self.args = args
		self.status = None

	def __eq__(self, obj):
		return self.id == obj.id

	def run(self, jmgr, os_target, sql):
		self.func(jmgr, os_target, sql, self.args)

class JobStatus:
	def __init__(self, id):
		self.id = id
		self.start_time = datetime.now()
		self.success = True

	def __eq__(self, obj):
		return self.id == obj.id

class WorkerProcess(Process):
	__count = 0

	@classmethod
	def get_worker_name(cls):
		cls.__count += 1
		return 'Worker-' + str(cls.__count)

	def __init__(self, scheduler):
		Process.__init__(self, name=WorkerProcess.get_worker_name())
		self.scheduler = scheduler

	def run(self):
		name = current_process().name
		print "Worker start running:", name
		logfile = name + ".log"
		if os.path.exists(logfile):
			os.system('cat ' + logfile + ' >> ' + logfile + '.bak')
		log = os.open(logfile, os.O_RDWR|os.O_CREAT|os.O_TRUNC)
		os.dup2(log, 1)
		os.dup2(log, 2)

		self.scheduler.sql.connect()
		while True:
			try:
				j = self.scheduler.worker_queue.get()
			except Empty:
				continue

			self.scheduler.workers.update([(name, j.id)])
			s = JobStatus(j.id)
			print "Start Job:", j.name, s.start_time
			try:
				j.run(self.scheduler, self.scheduler.os_target, self.scheduler.sql)
			except Exception as err:
				print err.__class__.__name__, ':', err
				print 'Traceback:'
				traceback.print_tb(sys.exc_info()[2])
				s.success = False
			s.end_time = datetime.now()
			print "Finish Job:", j.name, s.end_time
			self.scheduler.workers.update([(name, 0)])

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
						jobs.append(o)
						timeout = 0
					except Empty:
						break

				for j in jobs:
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

		print "Scheduler process started."

		Thread(target=receive_submission, args=(self.scheduler,)).start()
		Thread(target=receive_status, args=(self.scheduler,)).start()
		self.server.serve_forever()

class HostProcess(Process):
	def __init__(self, scheduler, host_server):
		Process.__init__(self)
		self.scheduler = scheduler
		self.host_server = host_server

	def run(self):
		id_alloc = Value('I', 1)
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

			def get_id():
				id = id_alloc.value
				id_alloc.value += 1
				return id

			SyncManagerScheduler.register('get_id', get_id)
			SyncManagerScheduler.register('get_jobs', callable=lambda: self.scheduler.jobs)
			SyncManagerScheduler.register('get_submit_queue', callable=lambda: self.scheduler.submit_queue)
			SyncManagerScheduler.register('get_worker_queue', callable=lambda: self.scheduler.worker_queue)
			SyncManagerScheduler.register('get_status_queue', callable=lambda: self.scheduler.status_queue)
			SyncManagerScheduler.register('get_exit_event', callable=lambda: self.scheduler.exit_event)
			SyncManagerScheduler.register('get_workers', callable=lambda: self.scheduler.workers)

			scheduler_server = SyncManagerScheduler(
					address=(self.scheduler.scheduler_host, self.scheduler.scheduler_port),
					authkey=self.scheduler.scheduler_auth
				).get_server()

			print "Scheduler listening at \"" + self.scheduler.scheduler_host + ":" + str(self.scheduler.scheduler_port) + "\"."
		except socket.error:
			print "Not scheduler server."
			pass

		if scheduler_server:
			self.scheduler_process = SchedulerProcess(self.scheduler, scheduler_server)
			self.scheduler_process.start()

		try:
			self.scheduler.connect()
		except socket.error:
			os._exit(0)

		self.worker_processes = []

		def receive_connection(server):
			server.serve_forever()

		Thread(target=receive_connection, args=(self.host_server,)).start()

		self.scheduler.exit_event.wait()

		if self.scheduler_process:
			print "Terminating scheduler process"
			self.scheduler_process.terminate()

		for w in self.worker_processes:
			print "Terminating worker process " + w.name
			w.terminate()

		host_file = root_dir + '/localserver.port'
		if os.path.exists(host_file):
			os.unlink(host_file)

		os._exit(0)

	def add_worker(self):
		w = WorkerProcess(self.scheduler)
		w.start()
		self.worker_processes.append(w)
		self.scheduler.workers.update([(w.name, 0)])

class SimpleScheduler(Scheduler):
	def __init__(self, os_target, sql):
		Scheduler.__init__(self, os_target, sql)

		self.scheduler_host = get_config('scheduler_host', default_scheduler_host)
		self.scheduler_port = get_config('scheduler_port', default_scheduler_port)
		self.scheduler_auth = get_config('scheduler_auth', default_scheduler_auth)

		host_file = root_dir + '/localserver.port'
		host_auth = root_dir
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

				SyncManagerHost.register('wait', callable=lambda: True)
				SyncManagerHost.register('add_worker', callable=add_worker)

				host_server = SyncManagerHost(
						address=(localhost, host_port),
						authkey=host_auth
					).get_server()

				print "Host listening at \"" + localhost + ":" + str(host_port) + "\"."
			except socket.error:
				pass

			if host_server:
				self.host_process = None
				child = os.fork()
				if child == 0:
					os.setsid()
					self.host_process = HostProcess(self, host_server)
					self.host_process.start()
					os._exit(0)
				else:
					os.waitpid(child, 0)

			try:
				class SyncManagerInterface(SyncManager):
					pass

				SyncManagerInterface.register('wait')
				SyncManagerInterface.register('add_worker')

				self.host_client = SyncManagerInterface(
						address=(localhost, host_port),
						authkey=host_auth
					)
				self.host_client.connect()
			except:
				host_port = None
				self.host_client = None

		self.host_client.wait()
		self.connect()

	def connect(self):
		class SyncManagerClient(SyncManager):
			pass

		SyncManagerClient.register('get_id')
		SyncManagerClient.register('get_jobs')
		SyncManagerClient.register('get_submit_queue')
		SyncManagerClient.register('get_worker_queue')
		SyncManagerClient.register('get_status_queue')
		SyncManagerClient.register('get_exit_event')
		SyncManagerClient.register('get_workers')

		self.client = SyncManagerClient(
				address=(self.scheduler_host, self.scheduler_port),
				authkey=self.scheduler_auth
			)
		self.client.connect()

		self.jobs = self.client.get_jobs()
		self.submit_queue = self.client.get_submit_queue()
		self.worker_queue = self.client.get_worker_queue()
		self.status_queue = self.client.get_status_queue()
		self.exit_event = self.client.get_exit_event()
		self.workers = self.client.get_workers()

	def add_worker(self):
		self.host_client.add_worker()

	def get_workers(self):
		return self.workers.items()

	def add_job(self, name, func, args):
		j = Job(self.client.get_id(), name, func, args)
		self.submit_queue.put(j)

	def requeue_job(self, id):
		try:
			j = self.jobs.get(id)
			self.add_job(j.name, j.func, j.args)
		except KeyError:
			pass

	def get_jobs(self):
		all_jobs = []
		for id in sorted(self.jobs.keys()):
			j = self.jobs.get(id)
			all_jobs.append((id, j.name, j.status))
		return all_jobs

	def clear_jobs(self):
		for j in self.jobs.values():
			if j.status is not None and j.status.success:
				try:
					self.jobs.pop(j.id)
				except KeyError:
					pass

	def exit(self):
		self.exit_event.set()
