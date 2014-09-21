#!/usr/bin/python

import os
import sys
import re
import importlib
import inspect

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
		query += ')'
		return query

	def insert_record(self, values):
		query = 'INSERT INTO ' + self.name + ' VALUES '
		delim = '('
		for (field, type, attr) in self.fields:
			query += delim
			delim = ', '
			if field in values:
				query += '\'' + str(values[field]) + '\''
			else:
				query += 'NULL'
		query += ')'
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
		return query

	def delete_record(self, condition):
		query = 'DELETE FROM ' + self.name
		if condition:
			query += ' WHERE ' + condition
		return query

	def update_record(self, values, condition):
		query = 'UPDATE ' + self.name + ' SET '
		delim = ''
		has_values = False
		for (field, type, attr) in self.fields:
			if field in values:
				has_values = True
				query += delim
				delim = ', '
				query += field + '=\'' + str(values[field]) + '\''
		if not has_values:
			raise Exception('syntax error: update ' + self.name)
		if condition:
			query += ' WHERE ' + condition
		return query

class SQL:
	def __init__(self):
		return

	# Have to implement following methods
	# def __del__(self):
	# def commit(self):
	# def connect_table(self, table):
	# def append_record(self, table, values):
	# def search_record(self, table, condition=None, fields=None):
	# def delete_record(self, table, condition=None):
	# def update_record(self, table, values, condition=None):

	@classmethod
	def get_engine(cls, name):
		names = name.split('.')
		obj = importlib.import_module(names[0])
		for n in names[1:]:
			next = None
			for (key, val) in inspect.getmembers(obj):
				if n == key:
					next = val
					break
			if not next:
				return None
			obj = next
		if not inspect.isclass(obj):
			return None
		if not issubclass(obj, SQL):
			return None
		return obj()

class SQLPrintQuery(SQL):
	def __init__(self):
		SQL.__init__(self)
		self.tables = []

	def __del__(self):
		return

	def commit(self):
		return

	def connect_table(self, table):
		if table in self.tables:
			return
		self.tables.append(table)
		print table.create_table()

	def append_record(self, table, values):
		print table.insert_record(values)

	def search_record(self, table, condition=None, fields=None):
		return None

	def delete_record(self, table, condition=None):
		print table.delete_record(condition)

	def update_record(self, table, values, condition=None):
		print table.update_record(values, condition)
