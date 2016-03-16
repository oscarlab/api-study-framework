#!/usr/bin/python

from task import Task
from sql import SQL
from package import binary_list_table, binary_link_table
from binary import get_binary_id, get_binary_name, get_package_id, get_package_name, package_id_table
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
	return "Analyze Library: " + args[1] + " in " + args[0]

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
	pkg_name = args[0]

	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analysis_linking(%d, lnk_id, True,  False) FROM binary_link WHERE pkg_id=%d AND linking=False' % (pkg_id, pkg_id))
	sql.postgresql_execute('SELECT analysis_linking(%d, bin_id, False, False) FROM binary_list WHERE pkg_id=%d AND linking=False and type != \'scr\'' % (pkg_id, pkg_id))
	sql.commit()

def AnalysisLinking_job_name(args):
	return "Analyze Linking: " + args[0]

AnalysisLinking = Task(
		name="Analyze Linking by PostgreSQL",
		func=AnalysisLinking_run,
		arg_defs=["package_name"],
		job_name=AnalysisLinking_job_name)

def AnalysisAllLinking_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)
	sql.connect_table(binary_link_table)

	results = sql.postgresql_query('SELECT DISTINCT pkg_id FROM binary_link WHERE linking=False UNION SELECT DISTINCT pkg_id FROM binary_list WHERE linking=False AND type != \'scr\'')

	for r in results:
		pkg_id = int(r[0])
		pkg_name = get_package_name(sql, pkg_id)
		if pkg_name:
			AnalysisLinking.create_job(jmgr, [pkg_name, pkg_id]);

def AnalysisAllLinking_job_name(args):
	return "Analyze All Linking"

AnalysisAllLinking = Task(
		name="Analyze All Linking by PostgreSQL",
		func=AnalysisAllLinking_run,
		arg_defs=[],
		job_name=AnalysisAllLinking_job_name)


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
	return "Analyze Executable: " + args[1] + " in " + args[0]

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

def AnalysisPackage_run(jmgr, sql, args):
	pkg_name = args[0]
	if len(args) > 1:
		pkg_id = args[1]
	else:
		pkg_id = get_package_id(sql, pkg_name)

	sql.postgresql_execute('SELECT analysis_package(%d)' % (pkg_id))
	sql.commit()

def AnalysisPackage_job_name(args):
	return "Analyze Package: " + args[0]

AnalysisPackage = Task(
		name="Analyze Package by PostgreSQL",
		func=AnalysisPackage_run,
		arg_defs=["Package Name"],
		job_name=AnalysisPackage_job_name)

def AnalysisAllPackages_run(jmgr, sql, args):
	sql.connect_table(package_id_table)

	results = sql.search_record(package_id_table, 'footprint=False', ['id'])

	for r in results:
		pkg_id = r[0]
		pkg_name = get_package_name(sql, pkg_id)
		if pkg_name:
			AnalysisPackage.create_job(jmgr, [pkg_name, pkg_id]);

def AnalysisAllPackages_job_name(args):
	return "Analyze All Packages"

AnalysisAllPackages = Task(
		name="Analyze All Packages by PostgreSQL",
		func=AnalysisAllPackages_run,
		arg_defs=[],
		job_name=AnalysisAllPackages_job_name)

def HashBinary_run(jmgr, sql, args):
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

	sql.postgresql_execute('SELECT hash_binary(%d, %d)' % (pkg_id, bin_id))
	sql.commit()

def HashBinary_job_name(args):
	return "Hash Binary: " + args[1] + " in " + args[0]

HashBinary = Task(
		name="Hash Binary by PostgreSQL",
		func=HashBinary_run,
		arg_defs=["Package Name", "Binary Name"],
		job_name=HashBinary_job_name)

def HashAllBinaries_run(jmgr, sql, args):
	sql.connect_table(binary_list_table)

	results = sql.search_record(binary_list_table, 'type!=\'scr\'', ['pkg_id', 'bin_id'])

	for r in results:
		values = r[0][1:-1].split(',')
		pkg_id = int(values[0])
		bin_id = int(values[1])
		pkg_name = get_package_name(sql, pkg_id)
		bin = get_binary_name(sql, bin_id)
		if pkg_name and bin:
			HashBinary.create_job(jmgr, [pkg_name, bin, pkg_id, bin_id]);

def HashAllBinaries_job_name(args):
	return "Hash All Binaries"

HashAllBinaries = Task(
		name="Hash All Binaries by PostgreSQL",
		func=HashAllBinaries_run,
		arg_defs=[],
		job_name=HashAllBinaries_job_name)

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

		#Task.register(AnalysisLibrary)
		Task.register(AnalysisAllLibraries)
		#Task.register(AnalysisLinking)
		Task.register(AnalysisAllLinking)
		#Task.register(AnalysisExecutable)
		Task.register(AnalysisAllExecutables)
		#Task.register(AnalysisPackage)
		Task.register(AnalysisAllPackages)
		#Task.register(HashBinary)
		Task.register(HashAllBinaries)

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
			while not self.postgresql_query(query):
				try:
					self.postgresql_execute(create_query)
					for q in table.create_indexes():
						self.postgresql_execute(q)
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
