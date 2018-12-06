#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import SQL, tables
from id import get_binary_id, get_binary_name, get_package_id, get_package_name
from utils import get_config
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

def AnalyzeLibrary(jmgr, os_target, sql, args):
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

subtasks['PostgresqlAnalyzeLibrary'] = Task(
		name = "Analyze Library by PostgreSQL",
		func = AnalyzeLibrary,
		arg_defs = ["Package Name", "Binary Name"],
		job_name = lambda args: "Analyze Library: " + args[1] + " in " + args[0])

def AnalyzeAllLibraries(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])

	results = sql.search_record(tables['binary_list'], 'callgraph=false AND type=\'lib\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin = get_binary_name(sql, bin_id)
		if pkg_name and bin:
			subtasks['PostgresqlAnalyzeLibrary'].create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

tasks['PostgresqlAnalyzeAllLibraries'] = Task(
		name="Analyze All Libaries by PostgreSQL",
		func=AnalyzeAllLibraries,
		order = 30)

def AnalyzeLinking(jmgr, os_target, sql, args):
	pkg_name = args[0]

	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analyze_linking(%d, lnk_id, true,  false) FROM binary_link WHERE pkg_id=%d AND linking=false' % (pkg_id, pkg_id))
	sql.postgresql_execute('SELECT analyze_linking(%d, bin_id, false, false) FROM binary_list WHERE pkg_id=%d AND linking=false and type != \'scr\'' % (pkg_id, pkg_id))
	sql.commit()

subtasks['PostgresqlAnalyzeLinking'] = Task(
		name = "Analyze Linking by PostgreSQL",
		func = AnalyzeLinking,
		arg_defs = ["package_name"],
		job_name = lambda args: "Analyze Linking: " + args[0])

def AnalyzeAllLinking(jmgr, os_target, sql, args):
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
			subtasks['PostgresqlAnalyzeLinking'].create_job(jmgr, [pkg_name, pkg_id]);

tasks['PostgresqlAnalyzeAllLinking'] = Task(
		name = "Analyze All Linking by PostgreSQL",
		func = AnalyzeAllLinking,
		order = 31)

def AnalyzeExecutable(jmgr, os_target, sql, args):
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

subtasks['PostgresqlAnalyzeExecutable'] = Task(
		name = "Analyze Executable by PostgreSQL",
		func = AnalyzeExecutable,
		arg_defs = ["Package Name", "Binary Name"],
		job_name = lambda args: "Analyze Executable: " + args[1] + " in " + args[0])

def AnalyzeAllExecutables(jmgr, os_target, sql, args):
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
			subtasks['PostgresqlAnalyzeExecutable'] \
				.create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

tasks['PostgresqlAnalyzeAllExecutables'] = Task(
		name = "Analyze All Executables by PostgreSQL",
		func = AnalyzeAllExecutables,
		order = 32)

def AnalyzePackage(jmgr, os_target, sql, args):
	pkg_name = args[0]
	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analyze_package(%d)' % (pkg_id))
	sql.commit()

subtasks['PostgresqlAnalyzePackage'] = Task(
		name = "Analyze Package by PostgreSQL",
		func = AnalyzePackage,
		arg_defs = ["Package Name"],
		job_name = lambda args: "Analyze Package: " + args[0])

def AnalyzeAllPackages(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_id'])

	results = sql.search_record(tables['package_id'], 'footprint=false', ['id'])

	for r in results:
		pkg_id = r[0]
		pkg_name = get_package_name(sql, pkg_id)
		if pkg_name:
			subtasks['PostgresqlAnalyzePackage'].create_job(jmgr, [pkg_name, pkg_id]);

tasks['PostgresqlAnalyzeAllPackages'] = Task(
		name = "Analyze All Packages by PostgreSQL",
		func = AnalyzeAllPackages,
		order = 33)

def AnalyzeExecutableSource(jmgr, os_target, sql, args):
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

	sql.postgresql_execute('SELECT analyze_executable_source(%d, %d)' % (pkg_id, bin_id))
	sql.commit()

subtasks['PostgresqlAnalyzeExecutableSource'] = Task(
		name = "Source of Opcodes in Executables",
		func = AnalyzeExecutableSource,
		arg_defs = ["Package Name", "Binary Name"],
		job_name = lambda args: "Analyze Executable Source: " + args[1] + " in " + args[0])

def AnalyzeAllExecutablesSources(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])

	results = sql.search_record(tables['binary_list'],
			'callgraph=false AND type=\'exe\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin_name = get_binary_name(sql, bin_id)
		if pkg_name and bin_name:
			subtasks['PostgresqlAnalyzeExecutableSource'] \
				.create_job(jmgr, [pkg_name, bin_name, pkg_id, bin_id]);

tasks['PostgresqlAnalyzeAllExecutablesSources'] = Task(
		name = "Analyze Sources of Opcodes in all Executables by PostgreSQL",
		func = AnalyzeAllExecutablesSources,
		order = 35)

def AnalyzePackageSource(jmgr, os_target, sql, args):
	pkg_name = args[0]
	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analyze_package_source(%d)' % (pkg_id))
	sql.commit()

subtasks['PostgresqlAnalyzePackageSource'] = Task(
		name = "Analyze Opcode Sources in a Package",
		func = AnalyzePackageSource,
		arg_defs = ["Package Name"],
		job_name = lambda args: "Analyze Package Source: " + args[0])

def AnalyzeAllPackagesSources(jmgr, os_target, sql, args):
	sql.connect_table(tables['package_id'])

	results = sql.search_record(tables['package_id'], 'footprint=false', ['id'])

	for r in results:
		pkg_id = r[0]
		pkg_name = get_package_name(sql, pkg_id)
		if pkg_name:
			subtasks['PostgresqlAnalyzePackageSource'].create_job(jmgr, [pkg_name, pkg_id]);

tasks['PostgresqlAnalyzeAllPackagesSources'] = Task(
		name = "Analyze Sources in All Packages by PostgreSQL",
		func = AnalyzeAllPackagesSources,
		order = 36)
