#!/usr/bin/python

from sql import SQL
from main import get_config

import os
import sys
import re
import sqlite3

class SQLite(SQL):
	def __init__(self):
		SQL.__init__(self)
		dbname = get_config('sqlite_db', 'syscall_popularity.db')
		self.db = sqlite3.connect(dbname)
		self.tables = []

	def __del__(self):
		self.db.close()

	def commit(self):
		self.db.commit()

	def sqlite_execute(self, query):
		retry = True
		while retry:
			retry = False
			try:
				self.db.execute(query)
			except sqlite3.OperationalError as err:
				if err.message != 'database is locked':
					print err.message + ':', query
					raise err
				retry = True

	def sqlite_query(self, query):
		retry = True
		while retry:
			cur = self.db.cursor()
			retry = False
			try:
				cur.execute(query)
				results = cur.fetchall()
			except sqlite3.OperationalError as err:
				if err.message != 'database is locked':
					cur.close()
					print err.message + ':', query
					raise err
				retry = True
			cur.close()
		return results

	def connect_table(self, table):
		if table not in self.tables:
			query = 'SELECT name FROM sqlite_master WHERE type=\'table\' AND name=\'' + table.name + '\''
			if not self.sqlite_query(query):
				self.sqlite_execute(table.create_table())
				self.db.commit()

			self.tables.append(table)

	def append_record(self, table, values):
		self.sqlite_execute(table.insert_record(values))

	def search_record(self, table, condition=None, fields=None):
		return self.sqlite_query(table.select_record(condition, fields))

	def delete_record(self, table, condition=None):
		self.sqlite_execute(table.delete_record(condition))

	def update_record(self, table, values, condition=None):
		self.sqlite_execute(table.update_record(values, condition))
