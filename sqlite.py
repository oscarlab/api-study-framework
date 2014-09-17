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

	def connect_table(self, table):
		if table not in self.tables:
			query = '''SELECT name FROM sqlite_master WHERE
				type=\'table\' AND name=\'''' + table.name + '\''
			retry = True
			while retry:
				cur = self.db.cursor()
				retry = False
				try:
					cur.execute(query)
					result = cur.fetchone()
				except sqlite3.OperationalError:
					retry = True
				cur.close()
			if not result:
				try:
					self.db.execute(table.create_table())
				except sqlite3.OperationalError:
					pass
				self.db.commit()
			self.tables.append(table)

	def append_record(self, table, values, commit=False):
		retry = True
		while retry:
			retry = False
			try:
				query = table.insert_record(values)
				self.db.execute(query)
			except sqlite3.OperationalError:
				retry = True
		if commit:
			self.db.commit()

	def search_record(self, table, condition=None, fields=None):
		retry = True
		while retry:
			cur = self.db.cursor()
			retry = False
			try:
				cur.execute(table.select_record(condition, fields))
				result = cur.fetchall()
			except sqlite3.OperationalError:
				retry = True
			cur.close()
		return result
