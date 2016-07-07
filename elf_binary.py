#!/usr/bin/python

from utils import null_dev

import os
import sys
import re
import subprocess

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
	process = subprocess.Popen(["readelf", "--dyn-syms", "-W", binary], stdout=subprocess.PIPE, stderr=null_dev)

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

	process = subprocess.Popen(["readelf", "--file-header","-W", binary], stdout=subprocess.PIPE, stderr=null_dev)

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

	process = subprocess.Popen(["readelf", "--section-headers", "-W", binary], stdout=subprocess.PIPE, stderr=null_dev)

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

# get_dependencies() will return list of dependencies that binary depends on.
def get_dependencies(binary):
	dependencies = set()

	process = subprocess.Popen(["readelf", "-d", "-W", binary], stdout=subprocess.PIPE, stderr=null_dev)

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
	process = subprocess.Popen(["readelf", "--program-headers", "-W", binary], stdout=subprocess.PIPE, stderr=null_dev)

	for line in process.stdout:
		line = line.strip()
		if not line.startswith('[Requesting program interpreter: '):
			continue

		return line[33:-1]

	if process.wait() != 0:
		raise Exception('process failed: readelf --program-headers')

	return None
