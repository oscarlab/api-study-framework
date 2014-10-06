#!/usr/bin/python

from sql import Table

import os
import sys
import re

binary_id_table = Table('binary_id', [
			('id', 'INT', 'NOT NULL'),
			('binary_name', 'VARCHAR', 'UNIQUE'),
			('file_name', 'VARCHAR', '')],
			['id'],
			[['file_name']])

def get_binary_id(sql, binary_name):
	sql.connect_table(binary_id_table)

	retry = True
	while retry:
		results = sql.search_record(binary_id_table, 'binary_name=\'' + Table.stringify(binary_name) + '\'', ['id'])
		if results:
			id = results[0][0]
			break

		results = sql.search_record(binary_id_table, None, ['MAX(id)'])
		if results[0][0] is None:
			id = 1
		else:
			id = int(results[0][0]) + 1

		values = dict()
		values['id'] = id
		values['binary_name'] = binary_name
		values['file_name'] = os.path.basename(binary_name)
		retry = False
		try:
			sql.append_record(binary_id_table, values)
			sql.commit()
		except:
			retry = True
			pass

	return id

def get_binary_name(sql, id):
	sql.connect_table(binary_id_table)
	results = sql.search_record(binary_id_table, 'id=\'' + Table.stringify(id) + '\'', ['binary_name'])
	if results:
		return results[0][0]
	return None

package_id_table = Table('package_id', [
			('id', 'INT', 'NOT NULL'),
			('package_name', 'VARCHAR', 'UNIQUE'),
			('footprint', 'BOOLEAN', '')],
			['id'],
			[['package_name']])

def get_package_id(sql, package_name):
	sql.connect_table(package_id_table)

	retry = True
	while retry:
		results = sql.search_record(package_id_table, 'package_name=\'' + Table.stringify(package_name) + '\'', ['id'])
		if results:
			id = results[0][0]
			break

		results = sql.search_record(package_id_table, None, ['MAX(id)'])
		if results[0][0] is None:
			id = 1
		else:
			id = int(results[0][0]) + 1

		values = dict()
		values['id'] = id
		values['package_name'] = package_name
		values['footprint'] = False
		retry = False
		try:
			sql.append_record(package_id_table, values)
			sql.commit()
		except:
			retry = True
			raise
			pass

	return id

def get_package_name(sql, id):
	sql.connect_table(package_id_table)
	results = sql.search_record(package_id_table, 'id=\'' + Table.stringify(id) + '\'', ['package_name'])
	if results:
		return results[0][0]
	return None
