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
				return None
			obj = next
		if not inspect.isclass(obj):
			return None
		if not issubclass(obj, OS):
			return None
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

def ApiList_run(jmgr, os_target, sql, args):
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

def ApiList_job_name(args):
	return "List API"

tasks['ApiList'] = Task(
		name="List APIs", func=ApiList_run)
