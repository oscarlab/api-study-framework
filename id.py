#!/usr/bin/python

from sql import tables, Table

import os
import sys
import re

tables['binary_id'] = Table('binary_id', [
			('id', 'INT', 'NOT NULL'),
			('binary_name', 'VARCHAR', 'UNIQUE'),
			('file_name', 'VARCHAR', '')],
			['id'], [['binary_name']])

def get_binary_id(sql, binary_name):
	sql.connect_table(tables['binary_id'])

	retry = True
	while retry:
		res = sql.search_record(tables['binary_id'], 'binary_name=' + Table.stringify(binary_name), ['id'])
		if len(res) > 0 and res[0][0]:
			id = res[0][0]
			break

		res = sql.search_record(tables['binary_id'], None, ['MAX(id)'])
		if res[0][0] == None:
			id = 1
		else:
			id = int(res[0][0]) + 1

		values = dict()
		values['id'] = id
		values['binary_name'] = binary_name
		values['file_name'] = os.path.basename(binary_name)
		retry = False
		try:
			sql.append_record(tables['binary_id'], values)
			sql.commit()
		except:
			retry = True
			pass

	return id

def get_binary_name(sql, id):
	sql.connect_table(tables['binary_id'])
	res = sql.search_record(tables['binary_id'], 'id=' + Table.stringify(id), ['binary_name'])
	if len(res) > 0 and res[0][0]:
		return res[0][0]
	return None

tables['package_id'] = Table('package_id', [
			('id', 'INT', 'NOT NULL'),
			('package_name', 'VARCHAR', 'UNIQUE'),
			('footprint', 'BOOLEAN', 'NOT NULL DEFAULT false'),
			('instr', 'BOOLEAN', 'NOT NULL DEFAULT false')],
			['id'], [['package_name']])

def get_package_id(sql, pkgname):
	sql.connect_table(tables['package_id'])

	retry = True
	while retry:
		res = sql.search_record(tables['package_id'], 'package_name=' + Table.stringify(pkgname), ['id'])
		if len(res) > 0 and res[0][0]:
			id = res[0][0]
			break

		res = sql.search_record(tables['package_id'], None, ['MAX(id)'])
		if res[0][0] == None:
			id = 1
		else:
			id = int(res[0][0]) + 1

		values = dict()
		values['id'] = id
		values['package_name'] = pkgname
		retry = False
		try:
			sql.append_record(tables['package_id'], values)
			sql.commit()
		except:
			retry = True
			pass

	return id

def get_package_name(sql, id):
	sql.connect_table(tables['package_id'])
	res = sql.search_record(tables['package_id'], 'id=' + Table.stringify(id), ['package_name'])
	if len(res) > 0 and res[0][0]:
		return res[0][0]
	return None
