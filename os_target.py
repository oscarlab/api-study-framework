#!/usr/bin/python

from sql import tables, Table
import sql
from task import tasks, Task

import inspect
import importlib

class OS:
	def __init__(self):
		return
	@classmethod
	def get_target(cls, name):
		names = name.split('.')
		obj = importlib.import_module(names[0])
		for n in names[1:]:
			next = None
			for (key, val) in inspect.getmembers(obj):
				if n == key:
					next = val
					break
			if not next:
				raise Exception('Object ' + name + ' is not found')
			obj = next
		if not inspect.isclass(obj):
			raise Exception('Object ' + name + ' is not a class')
		if not issubclass(obj, OS):
			raise Exception('Object ' + name + ' is not a subclass of OS')
		return obj()

tables['api_type'] = Table('api_type', [
		('type', 'SMALLINT', 'NOT NULL'),
		('name', 'VARCHAR(20)', 'NOT NULL')],
		['type'])

tables['api_list'] = Table('api_list', [
		('type', 'SMALLINT', 'NOT NULL'),
		('id', 'BIGINT', 'NOT NULL'),
		('name', 'VARCHAR', 'NOT NULL')],
		['type', 'id'])

def append_api_list(sql, type, id, name):
	sql.connect_table(tables['api_list'])

	retry = True
	while retry:
		res = sql.search_record(tables['api_list'], 'type=' + Table.stringify(type)  + ' and id=' + Table.stringify(id), ['name'])
		if len(res) > 0 and res[0][0]:
			if res[0][0] != name:
				raise Error('duplicate key value (' + Table.stringify(type) + ',' + Table.stringify(id) + ')')
			return

		values = dict()
		values['type'] = type
		values['id'] = id
		values['name'] = name
		retry = False
		try:
			sql.append_record(tables['api_list'], values)
			sql.commit()
		except:
			retry = True
			pass

def ApiList(jmgr, os_target, sql, args):
	sql.connect_table(tables['api_type'])
	sql.connect_table(tables['api_list'])

	api_types = os_target.get_api_types()
	apis = os_target.get_apis()

	sql.delete_record(tables['api_type'])
	for type_id, type_name in api_types.items():
		values = dict()
		values['type'] = type_id
		values['name'] = type_name
		sql.append_record(tables['api_type'], values)

	sql.delete_record(tables['api_list'])
	for values in apis:
		sql.append_record(tables['api_list'], values)

	sql.commit()

tasks['ApiList'] = Task(name = "List System APIs", func = ApiList, order = 20)
