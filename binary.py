#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_package_id, get_binary_id
import symbol
import callgraph

import os
import sys
import re

tables['binary_list'] = Table('binary_list', [
		('pkg_id', 'INT', 'NOT NULL'),
		('bin_id', 'INT', 'NOT NULL'),
		('type', 'CHAR(3)', 'NOT NULL'),
		('callgraph', 'BOOLEAN', 'NOT NULL DEFAULT false'),
		('linking', 'BOOLEAN', 'NOT NULL DEFAULT false')],
		['pkg_id', 'bin_id'],
		[['pkg_id', 'bin_id', 'type'], ['bin_id']])

tables['binary_link'] = Table('binary_link', [
		('pkg_id', 'INT', 'NOT NULL'),
		('lnk_id', 'INT', 'NOT NULL'),
		('target', 'INT', 'NOT NULL'),
		('linking', 'BOOLEAN', 'NOT NULL DEFAULT false')],
		['pkg_id', 'lnk_id'],
		[['lnk_id'], ['target']])

def append_binary_list(sql, pkgname, dir, binaries):
	sql.connect_table(tables['binary_list'])
	sql.connect_table(tables['binary_link'])
	sql.connect_table(tables['binary_interp'])

	pkg_id = get_package_id(sql, pkgname)
	insert_values = []

	for (bin, type, interpreter) in binaries:
		bin_id = get_binary_id(sql, bin)
		values = dict()
		values['type'] = type

		if type == 'lnk':
			link = os.readlink(dir + bin)
			target = os.path.join(os.path.dirname(bin), link)
			target_id = get_binary_id(sql, target)
			values['pkg_id'] = pkg_id
			values['lnk_id'] = bin_id
			values['target'] = target_id
			values['linking'] = False
		else:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			if type == 'scr':
				interp_id = get_binary_id(sql, interpreter)
				values['interp'] = interp_id
				values['callgraph'] = True
			else:
				values['callgraph'] = False
			values['linking'] = False

		insert_values.append(values)

	condition = 'pkg_id=' + Table.stringify(pkg_id)
	sql.delete_record(tables['binary_list'], condition)
	sql.delete_record(tables['binary_link'], condition)
	sql.delete_record(tables['binary_interp'], condition)

	for values in insert_values:
		if values['type'] == 'lnk':
			sql.append_record(tables['binary_link'], values)
		else:
			sql.append_record(tables['binary_list'], values)
			if values['type'] == 'scr':
				sql.append_record(tables['binary_interp'], values)
