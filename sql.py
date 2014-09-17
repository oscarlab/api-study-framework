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
		query += ');'
		return query

	def insert_record(self, values):
		query = 'REPLACE INTO ' + self.name + ' VALUES '
		delim = '('
		for (field, type, attr) in self.fields:
			query += delim
			delim = ', '
			query += '\'' + str(values[field]) + '\''
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
		print query
		return query

class SQL:
	def __init__(self):
		return

	# Have to implement following methods
	# def __del__(self):
	# def commit(self):
	# def connect_table(self, table):
	# def append_record(self, table, values, commit=False):
	# def search_record(self, table, condition=None, fields=None):

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
