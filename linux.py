from os_target import OS
import apt
import popcon
import main

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
	SYSCALL = 1
	FCNTL_SYSCALL = 72
	FCNTL = 2
	IOCTL_SYSCALL = 16
	IOCTL = 3
	PRCTL_SYSCALL = 157
	PRCTL = 4
	PSEUDOFILE = 5
	LIBC = 6

	def __init__(self):
		OS.__init__(self)
		apt.update_apt(main.get_config('package_source'))

	def get_api_types(self):
		return { self.SYSCALL: 'system call',
			 self.FCNTL: 'fcntl opcode',
			 self.IOCTL: 'ioctl opcode',
			 self.PRCTL: 'prctl opcode',
			 self.PSEUDOFILE: 'system file',
			 self.LIBC: 'libc function' }

	def get_apis(self):
		return [ { 'type': self.SYSCALL, 'id': number, 'name': name }
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
		return apt.unpack_package

	def get_binaries(self, dir, find_script=False):
		return elf_binary.get_binaries(dir, find_script)

	def get_binary_info(self, dir, name):
		return elf_binary.get_binary_info(os.path.join(dir, name))

	def get_binary_symbols(self, dir, name):
		return elf_binary.get_symbols(os.path.join(dir, name))

	def get_binary_dependencies(self, dir, name):
		return elf_binary.get_dependencies(os.path.join(dir, name))

	def analysis_binary_call(self, sql, dir, name, pkg_id, bin_id):
		objdump.analysis_binary_calls(sql, os.path.join(dir, name), pkg_id, bin_id)
