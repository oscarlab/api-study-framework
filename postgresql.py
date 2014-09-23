#!/usr/bin/python

from task import Task
from sql import SQL
from binary import get_binary_id, binary_id_table
from package import binary_list_table
from main import get_config

import os
import sys
import re
import psycopg2

def AnalysisCallgraph_run(jmgr, sql, args):
	binary_name = args[0]
	if args[1]:
		bin_id = int(args[1])
	else:
		bin_id = get_binary_id(sql, binary_name)

	sql.postgresql_execute('SELECT analysis_callgraph(%d)' % bin_id)
	sql.commit()

def AnalysisCallgraph_job_name(args):
	return "Analyze Callgraph: " + args[0]

AnalysisCallgraph = Task(
		name="Analyze Callgraph by PostgreSQL",
		func=AnalysisCallgraph_run,
		arg_defs=["Binary Name", "Binary ID"],
		job_name=AnalysisCallgraph_job_name)

def AnalysisAllCallgraph_run(jmgr, sql, args):
	sql.connect_table(binary_id_table)

	select = binary_list_table.select_record('bin_id=id AND type=\'lib\'')
	results = sql.search_record(binary_id_table,
			'callgraph_generated=\'False\' AND EXISTS (' + select + ')',
			['id', 'binary_name'])

	for r in results:
		values = r[0][1:-1].split(',')
		AnalysisCallgraph.create_job(jmgr, [values[1], values[0]]);

def AnalysisAllCallgraph_job_name(args):
	return "Analyze All Callgraph"

AnalysisAllCallgraph = Task(
		name="Analyze All Callgraph by PostgreSQL",
		func=AnalysisAllCallgraph_run,
		arg_defs=[],
		job_name=AnalysisAllCallgraph_job_name)

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

def AnalysisFootprint_run(jmgr, sql, args):
	binary_name = args[0]
	if args[1]:
		bin_id = int(args[1])
	else:
		bin_id = get_binary_id(sql, binary_name)

	sql.postgresql_execute('SELECT analysis_footprint(%d)' % bin_id)
	sql.commit()

def AnalysisFootprint_job_name(args):
	return "Analyze Footprint: " + args[0]

AnalysisFootprint = Task(
		name="Analyze Footprint by PostgreSQL",
		func=AnalysisFootprint_run,
		arg_defs=["Binary Name", "Binary ID"],
		job_name=AnalysisFootprint_job_name)

def AnalysisAllFootprint_run(jmgr, sql, args):
	sql.connect_table(binary_id_table)

	select = binary_list_table.select_record('bin_id=id AND type=\'exe\'')
	results = sql.search_record(binary_id_table,
			'footprint_generated=\'False\' AND EXISTS (' + select + ')',
			['id', 'binary_name'])

	for r in results:
		values = r[0][1:-1].split(',')
		AnalysisFootprint.create_job(jmgr, [values[1], values[0]]);

def AnalysisAllFootprint_job_name(args):
	return "Analyze All Footprint"

AnalysisAllFootprint = Task(
		name="Analyze All Footprint by PostgreSQL",
		func=AnalysisAllFootprint_run,
		arg_defs=[],
		job_name=AnalysisAllFootprint_job_name)

class PostgreSQL(SQL):
	def __init__(self):
		SQL.__init__(self)
		self.hostname = get_config('postgresql_host', 'localhost')
		self.username = get_config('postgresql_user', 'postgres')
		self.password = get_config('postgresql_pass', 'postgres')
		self.dbname = get_config('postgresql_db', 'syscall_popularity')
		self.db = None
		self.tables = []

		Task.register(AnalysisCallgraph)
		Task.register(AnalysisAllCallgraph)
		Task.register(AnalysisLinking)
		Task.register(AnalysisFootprint)
		Task.register(AnalysisAllFootprint)

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
			if not self.postgresql_query(query):
				self.postgresql_execute(table.create_table())
				self.db.commit()

			self.tables.append(table)

	def append_record(self, table, values):
		self.postgresql_execute(table.insert_record(values))

	def search_record(self, table, condition=None, fields=None):
		return self.postgresql_query(table.select_record(condition, fields))

	def delete_record(self, table, condition=None):
		self.postgresql_execute(table.delete_record(condition))

	def update_record(self, table, values, condition=None):
		self.postgresql_execute(table.update_record(values, condition))
