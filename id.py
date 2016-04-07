#!/usr/bin/python

from sql import Table

import os
import sys
import re

path_id_table = Table('path_id', [
			('id',		'INT',		'NOT NULL'),
			('path',	'VARCHAR',	'UNIQUE'),
			('basename',	'VARCHAR',	'')],
			['id'],
			[['basename']])

def get_path_id(sql, path):
	sql.connect_table(path_id_table)

	retry = True
	while retry:
		id = next(sql.search_record(path_id_table, 'path=\'' + Table.stringify(path) + '\'', ['id']), [None])[0]
		if id:
			break

		id = next(sql.search_record(path_id_table, None, ['MAX(id)']), [None])[0]
		if id is None:
			id = 1
		else:
			id = int(id) + 1

		values = dict()
		values['id'] = id
		values['path'] = path
		values['basename'] = os.path.basename(path)
		retry = False
		try:
			sql.append_record(path_id_table, values)
			sql.commit()
		except:
			retry = True
			pass

	return id

def get_path(sql, id):
	sql.connect_table(path_id_table)
	return next(sql.search_record(path_id_table, 'id=\'' + Table.stringify(id) + '\'', ['path']), [None])[0]

pkgname_id_table = Table('pkgname_id', [
			('id',		'INT',		'NOT NULL'),
			('pkgname',	'VARCHAR',	'UNIQUE')],
			['id'],
			[['pkgname']])

def get_pkgname_id(sql, pkgname):
	sql.connect_table(pkgname_id_table)

	retry = True
	while retry:
		id = next(sql.search_record(pkgname_id_table, 'pkgname=\'' + Table.stringify(pkgname) + '\'', ['id']), [None])[0]
		if id:
			break

		id = next(sql.search_record(pkgname_id_table, None, ['MAX(id)']), [None])[0]
		if id is None:
			id = 1
		else:
			id = int(id) + 1

		values = dict()
		values['id'] = id
		values['pkgname'] = pkgname
		retry = False
		try:
			sql.append_record(pkgname_id_table, values)
			sql.commit()
		except:
			retry = True
			pass

	return id

def get_pkgname(sql, id):
	sql.connect_table(pkgname_id_table)
	return next(sql.search_record(pkgname_id_table, 'id=\'' + Table.stringify(id) + '\'', ['pkgname']), [None])[0]

def get_pkgnames_by_prefix(sql, prefix):
	sql.connect_table(pkgname_id_table)
	for result in sql.search_record(package_id_table,
			'pkgname like \'' + Table.stringify(prefix) + '%\'',
			['id', 'pkgname']):
		yield result
