#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import SQL, tables
from id import get_binary_id, get_binary_name, get_package_id, get_package_name
from main import get_config
import binary

import os
import sys
import re
import psycopg2

class PostgreSQL(SQL):
	def __init__(self):
		SQL.__init__(self)
		self.hostname = get_config('postgresql_host', 'localhost')
		self.port     = get_config('postgresql_port', '5432')
		self.username = get_config('postgresql_user', 'postgres')
		self.password = get_config('postgresql_pass', 'postgres')
		self.dbname = get_config('postgresql_db', 'syscall_popularity')
		self.db = None
		self.tables = []

	def __del__(self):
		self.disconnect()

	def connect(self):
		self.db = psycopg2.connect(database=self.dbname, host=self.hostname, port=self.port, user=self.username, password=self.password)

	def disconnect(self):
		if self.db:
			self.db.close()
			self.db = None

	def commit(self):
		self.db.commit()

	def postgresql_execute(self, query):
		cur = self.db.cursor()
		try:
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
			create_query = table.create_table()
			retry = 10
			while not self.postgresql_query(query):
				try:
					self.postgresql_execute(create_query)
					for q in table.create_indexes():
						self.postgresql_execute(q)
					self.db.commit()
				except:
					retry = retry - 1
					if retry == 0:
						raise
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

	def hash_text(self, text):
		return self.postgresql_query('SELECT hashtext(\'' + text + '\')')[0][0]

def AnalysisLibrary(jmgr, os_target, sql, args):
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

	sql.postgresql_execute('SELECT analyze_library(%d, %d)' % (pkg_id, bin_id))
	sql.commit()

subtasks['PostgresqlAnalysisLibrary'] = Task(
		name = "Analyze Library by PostgreSQL",
		func = AnalysisLibrary,
		arg_defs = ["Package Name", "Binary Name"],
		job_name = lambda args: "Analyze Library: " + args[1] + " in " + args[0])

def AnalysisAllLibraries(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])

	results = sql.search_record(tables['binary_list'], 'callgraph=false AND type=\'lib\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin = get_binary_name(sql, bin_id)
		if pkg_name and bin:
			subtasks['PostgresqlAnalysisLibrary'].create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

tasks['PostgresqlAnalysisAllLibraries'] = Task(
		name="Analyze All Libaries by PostgreSQL",
		func=AnalysisAllLibraries)

def AnalysisLinking(jmgr, os_target, sql, args):
	pkg_name = args[0]

	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analyze_linking(%d, lnk_id, true,  false) FROM binary_link WHERE pkg_id=%d AND linking=false' % (pkg_id, pkg_id))
	sql.postgresql_execute('SELECT analyze_linking(%d, bin_id, false, false) FROM binary_list WHERE pkg_id=%d AND linking=false and type != \'scr\'' % (pkg_id, pkg_id))
	sql.commit()

subtasks['PostgresqlAnalysisLinking'] = Task(
		name = "Analyze Linking by PostgreSQL",
		func = AnalysisLinking,
		arg_defs = ["package_name"],
		job_name = lambda args: "Analyze Linking: " + args[0])

def AnalysisAllLinking(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])
	sql.connect_table(tables['binary_link'])

	results = sql.postgresql_query(
			'SELECT DISTINCT pkg_id FROM binary_link ' +
			'WHERE linking=false ' +
			'UNION SELECT DISTINCT pkg_id FROM binary_list ' +
			'WHERE linking=false AND type != \'scr\'')

	for r in results:
		pkg_id = int(r[0])
		pkg_name = get_package_name(sql, pkg_id)
		if pkg_name:
			subtasks['PostgresqlAnalysisLinking'].create_job(jmgr, [pkg_name, pkg_id]);

tasks['PostgresqlAnalysisAllLinking'] = Task(
		name = "Analyze All Linking by PostgreSQL",
		func = AnalysisAllLinking)

def AnalysisExecutable(jmgr, os_target, sql, args):
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

	sql.postgresql_execute('SELECT analyze_executable(%d, %d)' % (pkg_id, bin_id))
	sql.commit()

subtasks['PostgresqlAnalysisExecutable'] = Task(
		name = "Analyze Executable by PostgreSQL",
		func = AnalysisExecutable,
		arg_defs = ["Package Name", "Binary Name"],
		job_name = lambda args: "Analyze Executable: " + args[1] + " in " + args[0])

def AnalysisAllExecutables(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])

	results = sql.search_record(tables['binary_list'],
			'callgraph=false AND type=\'exe\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin = get_binary_name(sql, bin_id)
		if pkg_name and bin:
			subtasks['PostgresqlAnalysisExecutable'] \
				.create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

tasks['PostgresqlAnalysisAllExecutables'] = Task(
		name = "Analyze All Executables by PostgreSQL",
		func = AnalysisAllExecutables)

def AnalysisPackage(jmgr, os_target, sql, args):
	pkg_name = args[0]
	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analyze_package(%d)' % (pkg_id))
	sql.commit()

subtasks['PostgresqlAnalysisPackage'] = Task(
		name = "Analyze Package by PostgreSQL",
		func = AnalysisPackage,
		arg_defs = ["Package Name"],
		job_name = lambda args: "Analyze Package: " + args[0])

def AnalysisAllPackages(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_id'])

	results = sql.search_record(tables['package_id'], 'footprint=false', ['id'])

	for r in results:
		pkg_id = r[0]
		pkg_name = get_package_name(sql, pkg_id)
		if pkg_name:
			subtasks['PostgresqlAnalysisPackage'].create_job(jmgr, [pkg_name, pkg_id]);

tasks['PostgresqlAnalysisAllPackages'] = Task(
		name = "Analyze All Packages by PostgreSQL",
		func = AnalysisAllPackages)
