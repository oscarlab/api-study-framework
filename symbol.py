#!/usr/bin/python

from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_binary_id, get_package_id
import package

import os
import sys
import re
import subprocess
from multiprocessing import Value

tables['binary_symbol'] = Table('binary_symbol', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('symbol_name', 'VARCHAR', 'NOT NULL'),
			('version', 'VARCHAR', ''),
			('func_addr','INT', '')],
			['pkg_id', 'bin_id', 'symbol_name', 'version', 'func_addr'],
			[['symbol_name', 'version'], ['pkg_id', 'bin_id', 'func_addr'], ['pkg_id', 'bin_id']])

def BinarySymbol(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_list'])
	sql.connect_table(tables['binary_symbol'])

	pkgname = args[0]
	bin = args[1]
	dir = args[2]

	if len(args) > 3:
		ref = args[3]
		if not package.reference_exists(dir, ref):
			dir = None
			ref = None
	else:
		ref = None

	unpacked = False
	if not dir:
		(dir, pkgname, _) = package.unpack_package(os_target, args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		path = dir + '/' + bin
		if not os.path.exists(path):
			raise Exception('path ' + path + ' does not exist')

		symbols = os_target.get_binary_symbols(dir, bin)
		pkg_id = get_package_id(sql, pkgname)
		bin_id = get_binary_id(sql, bin)

		condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
		sql.delete_record(tables['binary_symbol'], condition)

		for sym in symbols:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['symbol_name'] = sym.name
			values['version'] = sym.version
			values['func_addr'] = sym.addr

			sql.append_record(tables['binary_symbol'], values)

		sql.update_record(tables['binary_list'], {'callgraph': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]

subtasks['BinarySymbol'] = Task(
	name = "Collect Binary Symbol",
	func = BinarySymbol,
	arg_defs = ["Package Name", "Binary Path", "Unpack Path"],
	job_name = lambda args: "Collect Binary Symbol: " + args[1] + " in " + args[0])

tables['binary_dependency'] = Table('binary_dependency', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('dependency', 'VARCHAR', 'NOT NULL')],
			['pkg_id', 'bin_id', 'dependency'],
			[['pkg_id', 'bin_id'], ['dependency']])

tables['binary_interp'] = Table('binary_interp', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('interp', 'INT', 'NOT NULL')],
			['pkg_id', 'bin_id'],
			[['interp']])

def BinaryDependency(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_dependency'])
	sql.connect_table(tables['binary_interp'])

	pkgname = args[0]
	bin = args[1]
	dir = args[2]

	if len(args) > 3:
		ref = args[3]
		if not package.reference_exists(dir, ref):
			dir = None
			ref = None
	else:
		ref = None

	unpacked = False
	if not dir:
		(dir, pkgname, _) = package.unpack_package(os_target, args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		if not os.path.exists(dir + bin):
			raise Exception('path ' + dir + bin + ' does not exist')

		dependencies = os_target.get_binary_dependencies(dir, bin)
		interp = os_target.get_binary_interpreter(dir, bin)
		pkg_id = get_package_id(sql, pkgname)
		bin_id = get_binary_id(sql, bin)
		if interp:
			interp = get_binary_id(sql, interp)

		condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
		sql.delete_record(tables['binary_dependency'], condition)
		sql.delete_record(tables['binary_interp'], condition)

		for dep in dependencies:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['dependency'] = dep
			sql.append_record(tables['binary_dependency'], values)

		if interp:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['interp'] = interp
			sql.append_record(tables['binary_interp'], values)

		sql.update_record(tables['binary_list'], {'linking': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]

subtasks['BinaryDependency'] = Task(
	name = "Collect Binary Dependency",
	func = BinaryDependency,
	arg_defs = ["Package Name", "Binary Path", "Unpack Path"],
	job_name = lambda args: "collect Binary Dependency: " + args[1] + " in " + args[0])
