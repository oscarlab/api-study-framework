#!/usr/bin/python

import os
import sys
import re
import sqlite3

class Table:
	def __init__(self, name, fields, keys=None):
		self.name = name
		self.fields = fields
		self.keys = keys

	def create_table(self):
		query = 'CREATE TABLE ' + self.name + ' '
		delim = '('
		for (name, type, attr) in self.fields:
			query += delim
			delim = ', '
			query += name + ' ' + type + ' ' + attr
		if self.keys:
			query += ', PRIMARY KEY '
			delim = '('
			for key in self.keys:
				query += delim
				delim = ', '
				query += key
			query += ')'
		query += ');'
		return query

	def insert_record(self, values):
		query = 'REPLACE INTO ' + self.name + ' VALUES '
		delim = '('
		for (field, type, attr) in self.fields:
			query += delim
			delim = ', '
			query += '\'' + values[field] + '\''
		query += ');'
		return query

	def select_record(self, condition, fields):
		query = 'SELECT '
		if fields:
			delim = '('
			for field in fields:
				query += delim
				delim = ', '
				query += field
			query += ')'
		else:
			query += '*'
		query += ' FROM ' + self.name
		if condition:
			query += ' WHERE ' + condition
		query += ';'
		return query

class SQLite:
	def __init__(self):
		self.db = sqlite3.connect('syscall_popularity.db')
		self.tables = []

	def __del__(self):
		self.db.close()

	def commit(self):
		self.db.commit()

	def connect_table(self, table):
		if table not in self.tables:
			query = '''SELECT name FROM sqlite_master WHERE
				type=\'table\' AND name=\'''' + table.name + '\''
			cur = self.db.cursor()
			cur.execute(query)
			if not cur.fetchone():
				self.db.execute(table.create_table())
				self.db.commit()
			self.tables.append(table)

	def append_record(self, table, values, commit=False):
		self.db.execute(table.insert_record(values))
		if commit:
			self.db.commit()

	def search_record(self, table, condition=None, fields=None):
		cur = self.db.cursor()
		cur.execute(table.select_record(condition, fields))
		return cur.fetchall()