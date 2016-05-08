from task import tasks, subtasks, Task
from sql import tables, Table
from binary import get_binary_id, get_package_id
import package
import main

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

tables['binary_api_usage_unknown'] = Table('binary_api_usage_unknonw', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('api_type', 'SMALLINT', ''),
			('api_id', 'BIGINT', '')],
			['pkg_id', 'bin_id', 'func_addr', 'target'],
			[['pkg_id', 'bin_id']])

def BinaryCall(jmgr, sql, args):
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
		(dir, pkgname, _) = package.unpack_package(args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		if not os.path.exists(os.path.join(dir, bin)):
			raise Exception('path ' + os.path.join(dir, bin) + ' does not exist')

		os_target.analysis_binary_call(sql, dir, bin,
					pkg_id, get_binary_id(sql, bin))

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

def BinaryCallInfo(jmgr, os_target, sql, args):
	(dir, pkgname, _) = package.unpack_package(args[0])
	if not dir:
		return

	binaries = os_target.get_binaries(dir)
	if not binaries:
		package.remove_dir(dir)
		return

	for (bin, type, _) in binaries:
		if type == 'lnk':
			continue
		ref = package.reference_dir(dir)
		tasks['BinaryCall'].create_job(jmgr, [pkgname, bin, dir, ref])

tasks['BinaryCallInfo'] = Task(
	name = "Collect Binary Call and APIs",
	func = BinaryCallInfo,
	arg_defs = ["Package Name"],
	job_name = lambda args: "Collect Binary Call and APIs: " + args[0])

def BinaryCallInfoByList(jmgr, os_target, sql, args):
	for pkg in package.pick_packages_from_args(os_target, sql, args):
		tasks['BinaryCallInfo'].create_job(jmgr, [pkg])

tasks['BinaryCallInfoByList'] = Task(
	name = "Collect Binary Call and APIs by Listing",
	func = BinaryCallInfoByList,
	arg_defs = package.args_to_pick_packages)
