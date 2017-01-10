from task import tasks, subtasks, Task
from sql import tables, Table
from id import get_binary_id, get_package_id
import package

import os
import sys
import re

tables['binary_call'] = Table('binary_call', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('call_addr', 'INT', ''),
			('call_name', 'VARCHAR', '')],
			[],
			[['pkg_id', 'bin_id']])

tables['binary_call_unknown'] = Table('binary_call_unknown', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('known', 'BOOLEAN', 'NOT NULL DEFAULT false'),
			('call_addr', 'INT', ''),
			('call_name', 'VARCHAR', '')],
			['pkg_id', 'bin_id', 'func_addr', 'target', 'known'],
			[['pkg_id', 'bin_id']])

tables['binary_api_usage'] = Table('binary_api_usage', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('api_type', 'SMALLINT', 'NOT NULL'),
			('api_id', 'BIGINT', 'NOT NULL')],
			['pkg_id', 'bin_id', 'func_addr', 'api_type', 'api_id'],
			[['pkg_id', 'bin_id'], ['pkg_id', 'bin_id', 'func_addr']])

tables['binary_api_usage_unknown'] = Table('binary_api_usage_unknown', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('known', 'BOOLEAN', 'NOT NULL DEFAULT false'),
			('api_type', 'SMALLINT', ''),
			('api_id', 'BIGINT', '')],
			['pkg_id', 'bin_id', 'func_addr', 'target', 'known'],
			[['pkg_id', 'bin_id']])

def BinaryCall(jmgr, os_target, sql, args):
	sql.connect_table(tables['binary_call'])
	sql.connect_table(tables['binary_call_unknown'])
	sql.connect_table(tables['binary_api_usage'])
	sql.connect_table(tables['binary_api_usage_unknown'])

	pkgname = args[0]
	bin = args[1]
	dir = args[2]
	pkg_id = get_package_id(sql, pkgname)

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

		bin_id = get_binary_id(sql, bin)
		os_target.analysis_binary_call(sql, dir, bin, pkg_id, bin_id)

		condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
		sql.update_record(tables['binary_list'], {'callgraph': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]


subtasks['BinaryCall'] = Task(
	name = "Collect Binary Call and APIs",
	func = BinaryCall,
	arg_defs = ["Package Name", "Binary Path", "Unpack Path"],
	job_name = lambda args: "Collect Binary Callgraph and API Usage: " + args[1] + " in " + args[0])
