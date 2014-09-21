#!/usr/bin/python

from sql import SQL
from main import get_config

import os
import sys
import re
import psycopg2

class PostgreSQL(SQL):
	def __init__(self):
		SQL.__init__(self)
		hostname = get_config('postgresql_host', 'localhost')
		username = get_config('postgresql_user', 'postgres')
		password = get_config('postgresql_pass', 'postgres')
		dbname = get_config('postgresql_db', 'syscall_popularity')
		self.db = psycopg2.connect(database=dbname, host=hostname, user=username, password=password)
		self.tables = []

	def __del__(self):
		self.db.close()

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
