#!/usr/bin/python

from task import Task
import package
from sql import Table

import os
import sys
import re
import subprocess
import shutil

# When the scope is D (Defined) , the libpath is the path where symbols is defined
# When the scope is U (Undefined) , the libpath gives the path where it is actually defined

class Symbol:
	def __init__(self, name, defined, version):
		self.name = name
		self.defined = defined
		self.version = version

	def __str__(self):
		return "Name: %50s\tScope: %2s\tVersion: %10s" % (self.name, self.scope, self.version)

def get_symbols(binary):
	process = subprocess.Popen(["readelf", "--dyn-syms", "-W", binary],
			stdout=subprocess.PIPE)

	symbol_list = []
	for line in process.stdout:
		parts = line.split()
		if len(parts) <= 7:
			continue
		if parts[3] != 'FUNC' and parts[3] != 'IFUNC':
			continue
		if parts[4] != 'GLOBAL' and parts[4] != 'WEAK':
			continue

		match = re.search('@', parts[7])
		if match:
			# Replace multiple occurences of @ with single @
			parts[7] = re.sub(r'@+', '@', parts[7])
			name, version = parts[7].split("@")
		else:
			name = parts[7]
			version = ''

		if parts[6] == 'UND':
			sym = Symbol(name, False, version)
			symbol_list.append(sym)
		elif parts[6].isdigit():
			sym = Symbol(name, True, version)
			symbol_list.append(sym)

	process.wait()
	return symbol_list

binary_symbol_table = Table('binary_symbol', [
			('binary', 'TEXT', 'NOT NULL'),
			('name', 'TEXT', 'NOT NULL'),
			('defined', 'BOOLEAN', 'NOT NULL'),
			('version', 'TEXT', '')],
			['binary', 'name'])

def BinarySymbol_run(jmgr, sql, args):
	sql.connect_table(binary_symbol_table)
	(dir, pkgname, version) = package.unpack_package(args[0])
	if not dir:
		return
	path = dir + '/' + args[1]
	if os.path.exists(path):
		symbols = get_symbols(path)
		for sym in symbols:
			values = dict()
			values['binary'] = args[1]
			values['name'] = sym.name
			if sym.defined:
				values['defined'] = 'True'
			else:
				values['defined'] = 'False'
			values['version'] = sym.version

			sql.append_record(binary_symbol_table, values)
	sql.commit()
	shutil.rmtree(dir)

def BinarySymbol_job_name(args):
	return "Binary Symbol: " + args[1] + " in " + args[0]

BinarySymbol = Task(
	name="Binary Symbol",
	func=BinarySymbol_run,
	arg_defs=["Package Name", "Binary Path"],
	job_name=BinarySymbol_job_name)

# get_dependencies() will return list of dependencies that binary depends on.
def get_dependencies(binary):
	process = subprocess.Popen(["ldd", binary], stdout=subprocess.PIPE)

	dependency_list = []
	for line in process.stdout:
		result = re.search('(lib[0-9A-Za-z_]+.so(.[0-9]+)?) =>', line)
		if result:
			dependency_list.append(result.group(1))
			continue
		result = re.search('(ld(-[0-9A-Za-z_\\-]+)?.so(.[0-9]+)?) ', line)
		if result:
			dependency_list.append(result.group(1))
			continue

	process.wait()
	return dependency_list

binary_dependency_table = Table('binary_dependency', [
			('binary', 'TEXT', 'NOT NULL'),
			('dependency', 'TEXT', 'NOT NULL')],
			['binary', 'dependency'])

def BinaryDependency_run(jmgr, sql, args):
	sql.connect_table(binary_dependency_table)
	(dir, pkgname, version) = package.unpack_package(args[0])
	if not dir:
		return
	path = dir + '/' + args[1]
	if os.path.exists(path):
		dependencies = get_dependencies(path)
		for dep in dependencies:
			values = dict()
			values['binary'] = args[1]
			values['dependency'] = dep

			sql.append_record(binary_dependency_table, values)
	sql.commit()
	shutil.rmtree(dir)

def BinaryDependency_job_name(args):
	return "Binary Dependency: " + args[1] + " in " + args[0]

BinaryDependency = Task(
	name="Binary Dependency",
	func=BinaryDependency_run,
	arg_defs=["Package Name", "Binary Path"],
	job_name=BinaryDependency_job_name)
