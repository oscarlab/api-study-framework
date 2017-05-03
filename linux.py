#!/usr/bin/python

from os_target import OS
import apt
import popcon
import elf_binary
import objdump
import objdump_isa
import objdump_linear
import linux_defs
from utils import get_config

import os
import sys
import re

def get_syscalls():
	files = [
		'/usr/include/x86_64-linux-gnu/asm/unistd_64.h',
		'/usr/include/asm/unistd_64.h',
	]

	unistd_file = None
	for f in files:
		if os.path.exists(f):
			unistd_file = f
			break

	if not unistd_file:
		raise Exception("Cannot find unistd file")

	syscalls = {}
	with open(unistd_file, 'r') as u:
		for line in u:
			match = re.match(r"^\#\s*define\s+__NR_([a-z0-9_]+)\s+([0-9]+)$", line)
			if match:
				syscalls[int(match.group(2))] = match.group(1)

	return syscalls

class Ubuntu64(OS):
	def __init__(self):
		OS.__init__(self)
		apt.update_apt(get_config('package_source'))

	def get_api_types(self):
		return { linux_defs.SYSCALL: 'system call',
			 linux_defs.FCNTL: 'fcntl opcode',
			 linux_defs.IOCTL: 'ioctl opcode',
			 linux_defs.PRCTL: 'prctl opcode',
			 linux_defs.PSEUDOFILE: 'system file',
			 linux_defs.LIBC: 'libc function' }

	def get_apis(self):
		return [ { 'type': linux_defs.SYSCALL, 'id': number, 'name': name }
				for number, name in get_syscalls().items() ]

	def get_packages(self):
		return apt.get_packages()

	def get_package_popularity(self):
		return popcon.get_package_popularity()

	def get_package_info(self, pkgname):
		return apt.get_package_info(pkgname)

	def get_package_dependency(self, pkgname):
		return apt.get_package_dependency(pkgname)

	def unpack_package(self, pkgname):
		return apt.unpack_package(pkgname)

	def get_binaries(self, dir, find_script=False):
		return apt.get_binaries(dir, find_script)

	def get_binary_info(self, dir, name):
		return elf_binary.get_binary_info(dir + name)

	def get_binary_symbols(self, dir, name):
		return elf_binary.get_symbols(dir + name)

	def get_binary_interpreter(self, dir, name):
		return elf_binary.get_interpreter(dir + name)

	def get_binary_dependencies(self, dir, name):
		return elf_binary.get_dependencies(dir + name)

	def analysis_binary_call(self, sql, dir, name, pkg_id, bin_id):
		objdump.analysis_binary_call(sql, dir + name, pkg_id, bin_id)

	def analysis_binary_instr(self, sql, dir, name, pkg_id, bin_id):
		objdump_isa.analysis_binary_instr(sql, dir + name, pkg_id, bin_id)

	def analysis_binary_instr_linear(self, sql, dir, name, pkg_id, bin_id):
		objdump_linear.analysis_binary_instr_linear(sql, dir + name, pkg_id, bin_id)
	def emit_corpus(self, bin, file):
		objdump_linear.emit_corpus(bin, file)
