#!/usr/bin/python

from task import Task
import package
from sql import Table
from binary import get_binary_id, get_package_id
import main

import os
import sys
import re
import subprocess
from multiprocessing import Value

# When the scope is D (Defined) , the libpath is the path where symbols is defined
# When the scope is U (Undefined) , the libpath gives the path where it is actually defined

class Symbol:
	def __init__(self, name, defined, addr, version):
		self.name = name
		self.defined = defined
		self.addr = addr
		self.version = version

	def __str__(self):
		return "Addr: %08x\tName: %50s\tScope: %2s\tVersion: %10s" % (self.addr, self.name, self.scope, self.version)

	def __eq__(self, obj):
		return self.name == obj.name and self.version == obj.version

def get_symbols(binary):
	process = subprocess.Popen(["readelf", "--dyn-syms", "-W", binary], stdout=subprocess.PIPE, stderr=main.null_dev)

	symbol_list = []
	for line in process.stdout:
		parts = line.split()
		if len(parts) <= 7:
			continue
		if parts[3] != 'FUNC' and parts[3] != 'IFUNC':
			continue
		if parts[4] == 'LOCAL':
			continue

		match = re.search('@', parts[7])
		if match:
			# Replace multiple occurences of @ with single @
			parts[7] = re.sub(r'@+', '@', parts[7])
			name, version = parts[7].split("@")
		else:
			name = parts[7]
			version = ''

		addr = int(parts[1], 16)

		if parts[6] == 'UND':
			sym = Symbol(name, False, 0, version)
			if sym not in symbol_list:
				symbol_list.append(sym)
		elif parts[6].isdigit():
			sym = Symbol(name, True, addr, version)
			if sym not in symbol_list:
				symbol_list.append(sym)

	process.wait()

	process = subprocess.Popen(["readelf", "--file-header","-W", binary], stdout=subprocess.PIPE, stderr=main.null_dev)

	entry_addr = None
	for line in process.stdout:
		results = re.match(r"([^\:]+)\: +(.+)", line.strip())
		if results:
			key = results.group(1)
			val = results.group(2)
			if key == 'Entry point address':
				addr = int(val[2:], 16)
				sym = Symbol('.entry', True, addr, '')
				if sym not in symbol_list:
					symbol_list.append(sym)
				break

	process.wait()

	process = subprocess.Popen(["readelf", "--section-headers", "-W", binary], stdout=subprocess.PIPE, stderr=main.null_dev)

	for line in process.stdout:
		parts = line[6:].strip().split()
		if len(parts) < 2:
			continue
		if parts[0] in ['.init', '.init_array', '.fini', '.fini_array']:
			addr = int(parts[2], 16)
			sym = Symbol(parts[0], True, addr, '')
			if sym not in symbol_list:
				symbol_list.append(sym)
	process.wait()

	return symbol_list

binary_symbol_table = Table('binary_symbol', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('symbol_name', 'VARCHAR', 'NOT NULL'),
			('defined', 'BOOLEAN', 'NOT NULL'),
			('func_addr','INT', ''),
			('version', 'VARCHAR', '')],
			['pkg_id', 'bin_id', 'symbol_name', 'version'],
			[['symbol_name'], ['pkg_id', 'bin_id', 'func_addr'], ['pkg_id', 'bin_id']])

def BinarySymbol_run(jmgr, sql, args):
	sql.connect_table(binary_symbol_table)
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
		(dir, pkgname, _) = package.unpack_package(args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		path = dir + '/' + bin
		if not os.path.exists(path):
			raise Exception('path ' + path + ' does not exist')

		symbols = get_symbols(path)
		pkg_id = get_package_id(sql, pkgname)
		bin_id = get_binary_id(sql, bin)

		condition = 'pkg_id=\'' + Table.stringify(pkg_id) + '\' and bin_id=\'' + Table.stringify(bin_id) + '\''
		sql.delete_record(binary_symbol_table, condition)

		for sym in symbols:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['symbol_name'] = sym.name
			if sym.defined:
				values['defined'] = 'True'
			else:
				values['defined'] = 'False'
			values['func_addr'] = sym.addr
			values['version'] = sym.version

			sql.append_record(binary_symbol_table, values)

		sql.update_record(package.binary_list_table, {'callgraph': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]

def BinarySymbol_job_name(args):
	return "Binary Symbol: " + args[1] + " in " + args[0]

BinarySymbol = Task(
	name="Binary Symbol",
	func=BinarySymbol_run,
	arg_defs=["Package Name", "Binary Path", "Unpack Path"],
	job_name=BinarySymbol_job_name)

# get_dependencies() will return list of dependencies that binary depends on.
def get_dependencies(binary):
	dependencies = set()

	process = subprocess.Popen(["readelf", "-d", "-W", binary], stdout=subprocess.PIPE, stderr=main.null_dev)

	for line in process.stdout:
		parts = line.strip().split()
		if len(parts) < 5:
			continue
		if parts[1] == '(NEEDED)' and parts[2] == 'Shared' and parts[3] == 'library:':
			dependencies.add(parts[4][1:-1])

	if process.wait() != 0:
		raise Exception('process failed: readelf -d')

	return dependencies

# get_interpreter() will return the name of interpreter.
def get_interpreter(binary):
	process = subprocess.Popen(["readelf", "--program-headers", "-W", binary], stdout=subprocess.PIPE, stderr=main.null_dev)

	for line in process.stdout:
		line = line.strip()
		if not line.startswith('[Requesting program interpreter: '):
			continue

		return line[33:-1]

	if process.wait() != 0:
		raise Exception('process failed: readelf --program-headers')

	return None

binary_dependency_table = Table('binary_dependency', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('dependency', 'VARCHAR', 'NOT NULL')],
			['pkg_id', 'bin_id', 'dependency'],
			[['pkg_id', 'bin_id'], ['dependency']])

binary_interp_table = Table('binary_interp', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('interp', 'INT', 'NOT NULL')],
			['pkg_id', 'bin_id'],
			[['interp']])

def BinaryDependency_run(jmgr, sql, args):
	sql.connect_table(binary_dependency_table)
	sql.connect_table(binary_interp_table)
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
		(dir, pkgname, _) = package.unpack_package(args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		path = dir + '/' + bin
		if not os.path.exists(path):
			raise Exception('path ' + path + ' does not exist')

		dependencies = get_dependencies(path)
		interp = get_interpreter(path)
		pkg_id = get_package_id(sql, pkgname)
		bin_id = get_binary_id(sql, bin)
		if interp:
			interp = get_binary_id(sql, interp)

		dependencies = get_dependencies(path)

		condition = 'pkg_id=\'' + Table.stringify(pkg_id) + '\' and bin_id=\'' + Table.stringify(bin_id) + '\''
		sql.delete_record(binary_dependency_table, condition)
		sql.delete_record(binary_interp_table, condition)

		for dep in dependencies:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['dependency'] = dep
			sql.append_record(binary_dependency_table, values)

		if interp:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['interp'] = interp
			sql.append_record(binary_interp_table, values)

		sql.update_record(package.binary_list_table, {'linking': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]

def BinaryDependency_job_name(args):
	return "Binary Dependency: " + args[1] + " in " + args[0]

BinaryDependency = Task(
	name="Binary Dependency",
	func=BinaryDependency_run,
	arg_defs=["Package Name", "Binary Path", "Unpack Path"],
	job_name=BinaryDependency_job_name)

def BinaryInfo_run(jmgr, sql, args):
	(dir, pkgname, _) = package.unpack_package(args[0])
	if not dir:
		return
	binaries = package.walk_package(dir)
	if not binaries:
		package.remove_dir(dir)
		return
	for (bin, type, _) in binaries:
		if type == 'lnk':
			continue
		ref = package.reference_dir(dir)
		BinaryDependency.create_job(jmgr, [pkgname, bin, dir, ref])
		ref = package.reference_dir(dir)
		BinarySymbol.create_job(jmgr, [pkgname, bin, dir, ref])

def BinaryInfo_job_name(args):
	return "Binary Info: " + args[0]

BinaryInfo = Task(
	name="Binary Info",
	func=BinaryInfo_run,
	arg_defs=["Package Name"],
	job_name=BinaryInfo_job_name)

def BinaryInfoByNames_run(jmgr, sql, args):
	packages = package.get_packages_by_names(args[0].split())
	if packages:
		for i in packages:
			BinaryInfo.create_job(jmgr, [i])

def BinaryInfoByNames_job_name(args):
	return "Binary Info By Names: " + args[0]

BinaryInfoByNames = Task(
	name="Binary Info By Names",
	func=BinaryInfoByNames_run,
	arg_defs=["Package Names"],
	job_name=BinaryInfoByNames_job_name)

def BinaryInfoByPrefixes_run(jmgr, sql, args):
	packages = package.get_packages_by_prefixes(args[0].split())
	if packages:
		for i in packages:
			BinaryInfo.create_job(jmgr, [i])

def BinaryInfoByPrefixes_job_name(args):
	return "Binary Info By Prefixes: " + args[0]

BinaryInfoByPrefixes = Task(
	name="Binary Info By Prefixes",
	func=BinaryInfoByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=BinaryInfoByPrefixes_job_name)

def BinaryInfoByRanks_run(jmgr, sql, args):
	packages = package.get_packages_by_ranks(sql, int(args[0]), int(args[1]))
	if packages:
		for i in packages:
			BinaryInfo.create_job(jmgr, [i])

def BinaryInfoByRanks_job_name(args):
	return "Binary Info By Ranks: " + args[0] + " to " + args[1]

BinaryInfoByRanks = Task(
	name="Binary Info By Ranks",
	func=BinaryInfoByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=BinaryInfoByRanks_job_name)
