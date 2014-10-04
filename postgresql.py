#!/usr/bin/python

from task import Task
from sql import SQL
from package import binary_list_table
from binary import get_binary_id, get_binary_name, get_package_id, get_package_name
from main import get_config

import os
import sys
import re
import psycopg2

def AnalysisLibrary_run(jmgr, sql, args):
	pkg_name = args[0]
	bin = args[1]

	if args[2]:
		pkg_id = args[2]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	if args[3]:
		bin_id = args[3]
	else:
		bin_id = get_binary_id(sql, bin)

	sql.postgresql_execute('SELECT analysis_library(%d, %d)' % (pkg_id, bin_id))
	sql.commit()

def AnalysisLibrary_job_name(args):
	return "Analyze Library: " + args[0]

AnalysisLibrary = Task(
		name="Analyze Library by PostgreSQL",
		func=AnalysisLibrary_run,
		arg_defs=["Package Name", "Binary Name"],
		job_name=AnalysisLibrary_job_name)

def AnalysisAllLibraries_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)

	results = sql.search_record(binary_list_table, 'callgraph=False AND type=\'lib\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin = get_binary_name(sql, bin_id)
		if pkg_name and bin:
			AnalysisLibrary.create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

def AnalysisAllLibraries_job_name(args):
	return "Analyze All Libraries"

AnalysisAllLibraries = Task(
		name="Analyze All Libaries by PostgreSQL",
		func=AnalysisAllLibraries_run,
		arg_defs=[],
		job_name=AnalysisAllLibraries_job_name)

def AnalysisLinking_run(jmgr, sql, args):
	sql.postgresql_execute('SELECT analysis_linking()')
	sql.commit()

def AnalysisLinking_job_name(args):
	return "Analyze Linking"

AnalysisLinking = Task(
		name="Analyze Linking by PostgreSQL",
		func=AnalysisLinking_run,
		arg_defs=[],
		job_name=AnalysisLinking_job_name)

def AnalysisExecutable_run(jmgr, sql, args):
	pkg_name = args[0]
	bin = args[1]
	if len(args) > 2:
		pkg_id = args[2]
	else:
		pkg_id = get_package_id(sql, pkg_name)
	if len(args) > 3:
		bin_id = args[3]
	else:
		bin_id = get_binary_id(sql, bin)

	sql.postgresql_execute('SELECT analysis_executable(%d, %d)' % (pkg_id, bin_id))
	sql.commit()

def AnalysisExecutable_job_name(args):
	return "Analyze Executable: " + args[0]

AnalysisExecutable = Task(
		name="Analyze Executable by PostgreSQL",
		func=AnalysisExecutable_run,
		arg_defs=["Package Name", "Binary Name"],
		job_name=AnalysisExecutable_job_name)

def AnalysisAllExecutables_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)

	results = sql.search_record(binary_list_table, 'callgraph=False AND type=\'exe\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin = get_binary_name(sql, bin_id)
		if pkg_name and bin:
			AnalysisExecutable.create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

def AnalysisAllExecutables_job_name(args):
	return "Analyze All Executables"

AnalysisAllExecutables = Task(
		name="Analyze All Executables by PostgreSQL",
		func=AnalysisAllExecutables_run,
		arg_defs=[],
		job_name=AnalysisAllExecutables_job_name)

class PostgreSQL(SQL):
	def __init__(self):
		SQL.__init__(self)
		self.hostname = get_config('postgresql_host', 'localhost')
		self.username = get_config('postgresql_user', 'postgres')
		self.password = get_config('postgresql_pass', 'postgres')
		self.dbname = get_config('postgresql_db', 'syscall_popularity')
		self.db = None
		self.tables = []

		Task.register(AnalysisLibrary)
		Task.register(AnalysisAllLibraries)
		Task.register(AnalysisLinking)
		Task.register(AnalysisExecutable)
		Task.register(AnalysisAllExecutables)

	def __del__(self):
		self.disconnect()

	def connect(self):
		self.db = psycopg2.connect(database=self.dbname, host=self.hostname, user=self.username, password=self.password)

	def disconnect(self):
		if self.db:
			self.db.close()
			self.db = None

	def commit(self):
		self.db.commit()

	def postgresql_execute(self, query):
		cur = self.db.cursor()
		try:
			print query
			cur.execute(query)
		except psycopg2.Error as err:
			cur.close()
			self.db.rollback()
			raise err
		cur.close()
	
	def postgresql_query(self, query):
		cur = self.db.cursor()
		try:
			cur.execute(query)
			results = cur.fetchall()
		except psycopg2.Error as err:
			cur.close()
			self.db.rollback()
			raise err
		cur.close()
		return results

	def connect_table(self, table):
		if table not in self.tables:
			query = 'SELECT relname FROM pg_class WHERE relname=\'' + table.name + '\''
			while not self.postgresql_query(query):
				try:
					self.postgresql_execute(table.create_table())
					for query in table.create_indexes():
						self.postgresql_execute(query)
					self.db.commit()
				except:
					continue
				break

			self.tables.append(table)

	def append_record(self, table, values):
		self.postgresql_execute(table.insert_record(values))

	def search_record(self, table, condition=None, fields=None):
		return self.postgresql_query(table.select_record(condition, fields))

	def delete_record(self, table, condition=None):
		self.postgresql_execute(table.delete_record(condition))

	def update_record(self, table, values, condition=None):
		self.postgresql_execute(table.update_record(values, condition))
