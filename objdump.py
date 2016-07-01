#!/usr/bin/python

from sql import tables, Table
from id import get_binary_id, get_package_id
from elf_binary import get_symbols
import package
import linux_defs
import os_target
from utils import null_dev

import os
import sys
import re
import subprocess
import struct
import string

def is_hex(s):
	try:
		int(s, 16)
		return True
	except ValueError:
		return False

class Caller:
	def __init__(self, func_addr, func_name):
		self.func_addr = func_addr
		self.func_name = func_name
		self.callees = set()
		self.syscalls = set()
		self.vecsyscalls = {cs['syscall']: set() for cs in Vec_Syscall_Inst.syscalls}
		self.files = set()
		self.closed = False

	def add_callees(self, callees):
		if callees:
			self.callees |= set(callees)

	def add_syscalls(self, syscalls):
		if syscalls:
			self.syscalls |= set(syscalls)

	def add_vecsyscalls(self, syscalls):
		if syscalls:
			for (s, req) in syscalls:
				self.vecsyscalls[s] |= set([req])

	def add_files(self, files):
		if files:
			self.files |= set(files)

	@classmethod
	def register_caller(cls, caller_list, func_addr, func_name = None,
			callees=[], syscalls=[]):
		caller = None
		for item in caller_list:
			if func_name:
				if item.func_name != func_name:
					continue
			else:
				if item.func_addr != func_addr:
					continue
			caller = item
			break
		if not caller:
			caller = Caller(func_addr, func_name)
			caller_list.append(caller)

		# Merge two
		caller.add_callees(callees)
		caller.add_syscalls(syscalls)

	def __str__(self):
		result = '%08x: %s' % (self.func_addr, self.func_name)
		for c in self.callees:
			if isinstance(c, int):
				result += "\n\tcall: " + "%08x" % (c)
			else:
				result += "\n\tcall: " + c
		for s in self.syscalls:
			if isinstance(s, int) and s in syscall.syscalls:
				result += "\n\tsyscall: " + syscall.syscalls[s]
			else:
				result += "\n\tsyscall: " + str(s)
		for s in self.vecsyscalls:
			for req in self.vecsyscalls[s]:
				result += "\n\t" + syscall.syscalls[s] + ": " + str(req)
		for f in self.files:
			result += "\n\tfile: " + f
		if self.closed:
			result += "\n\tfunction closed"
		return result

class Inst:
	def __init__(self, inst_addr):
		if not isinstance(inst_addr, int):
			raise Exception('has to be an integer')
		self.inst_addr = inst_addr

	def __str__(self):
		return '%08x:' % (self.inst_addr)

class Call_Inst(Inst):
	def __init__(self, inst_addr, call_addr=0, call_name=None, target=''):
		Inst.__init__(self, inst_addr)
		self.call_addr = call_addr
		self.call_name = call_name
		self.target = target

	def __str__(self):
		if self.call_addr and self.call_name:
			return Inst.__str__(self) + ' call 0x%08x: ' % (self.call_addr) + self.call_name
		if self.call_addr:
			return Inst.__str__(self) + ' call 0x%08x' % (self.call_addr)
		if self.call_name:
			return Inst.__str__(self) + ' call ' + self.call_name

		return Inst.__str__(self) + ' call ' + self.target

class Syscall_Inst(Inst):
	def __init__(self, inst_addr, assign=None, syscall=-1, target=''):
		Inst.__init__(self, inst_addr)
		self.assign = assign
		self.syscall = syscall
		if isinstance(target, str):
			self.target = target
		else:
			self.target = '@%x' % (inst_addr)

	@classmethod
	def is_valid(cls, num):
		if isinstance(num, int) and num >= 0 and num < 1024:
			return True
		return False

	def __str__(self):
		if self.syscall != -1:
			return Inst.__str__(self) + ' syscall ' + str(self.syscall)

		return Inst.__str__(self) + ' syscall ' + self.target

class Vec_Syscall_Inst(Syscall_Inst):
	syscalls = [
		{'syscall': linux_defs.FCNTL_SYSCALL, 'func_addr': 0, 'func_name':  'fcntl', 'reg': ('%rsi', '%rdx')},
		{'syscall': linux_defs.IOCTL_SYSCALL, 'func_addr': 0, 'func_name':  'ioctl', 'reg': ('%rsi', '%rdx')},
		{'syscall': linux_defs.PRCTL_SYSCALL, 'func_addr': 0, 'func_name':  'prctl', 'reg': ('%rdi', '%rsi')},
	]

	@classmethod
	def get_compound(cls, syscall=None, func_addr=None, func_name=None):
		if syscall is not None and isinstance(syscall, int):
			for s in Vec_Syscall_Inst.syscalls:
				if syscall == s['syscall']:
					return s

		if func_addr is not None:
			for s in Vec_Syscall_Inst.syscalls:
				if func_addr == s['func_addr']:
					return s

		if func_name is not None:
			for s in Vec_Syscall_Inst.syscalls:
				if func_name == s['func_name']:
					return s

		return None

	@classmethod
	def is_valid(cls, req):
		if isinstance(req, int) and req >= 0:
			return True
		if isinstance(req, long) and req >= 0 and req <= 0xffffffff:
			return True
		return False

	def __init__(self, inst_addr, assign=None, syscall=-1, target='', req_assign=None, req=-1, req_target=''):
		Syscall_Inst.__init__(self, inst_addr, assign, syscall, target)
		self.req_assign = req_assign
		self.req = req
		self.req_target = req_target

	def __str__(self):
		if self.req != -1:
			return 'compound ' + Syscall_Inst.__str__(self) + ' by ' + str(self.req)

		return 'compound ' + Syscall_Inst.__str__(self) + ' by ' + self.req_target

def get_fileaccess(binary_name):
	file_list = []
        binary = open(binary_name, 'rb')
	path = None
	lino = 0
	while True:
		try:
			ch = struct.unpack('s', binary.read(1))[0]
		except:
			break

		if ch == '/':
			path = ch
			while True:
				ch = struct.unpack('s', binary.read(1))[0]
				if ch == '\0' or ch in string.whitespace or ch == '\'' or ch == '\"':
					break
				if ch not in string.printable:
					path = None
					break
				path += ch
			if path:
				path = path.rstrip(string.punctuation)
				for prefix in File_Inst.prefixes:
					if path.startswith(prefix):
						file_list.append(re.sub(r'\%[0-9\.\+\-]*[A-Za-z]', '*', path))
		elif ch is None:
			break
		else:
			continue
	binary.close()
	return file_list

class File_Inst(Inst):
	prefixes = ['/proc', '/dev', '/sys', '/etc']

	def __init__(self, inst_addr, file):
		Inst.__init__(self, inst_addr)
		self.file = re.sub(r'\%[0-9\.\+\-]*[A-Za-z]', '*', file)

	def __str__(self):
		return Inst.__str__(self) + ' access ' + self.file

def get_callgraph(binary_name):
	process = subprocess.Popen(["readelf", "--file-header", "-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

	entry_addr = None
	for line in process.stdout:
		results = re.match(r"([^\:]+)\: +(.+)", line.strip())
		if results:
			key = results.group(1)
			val = results.group(2)
			if key == 'Class' and val != 'ELF64':
				raise Exception('Unsupported class: ' + val)
			if key == 'Entry point address':
				entry_addr = int(val[2:], 16)

	if process.wait() != 0:
		raise Exception('process failed: readelf --file-header')

	process = subprocess.Popen(["readelf", "--dyn-syms","-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

	dynsym_list = {}
	for line in process.stdout:
		parts = line.strip().split()
		if len(parts) < 8:
			continue
		if not is_hex(parts[1]):
			continue
		match = re.match(r"([A-Za-z0-9_]+)(@@?[A-Za-z0-9_\.]+)?$", parts[7])
		if not match:
			continue
		addr = int(parts[1], 16)
		if not addr:
			continue
		symbol_name = match.group(1)
		dynsym_list[addr] = symbol_name

		for cs in Vec_Syscall_Inst.syscalls:
			if cs['func_name'] == symbol_name:
				cs['func_addr'] = addr

	if process.wait() != 0:
		raise Exception('process failed: readelf --dyn-syms')

	process = subprocess.Popen(["readelf", "--program-headers", "-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

	load_list = []
	for line in process.stdout:
		parts = line.strip().split()
		if len(parts) < 6:
			continue
		if parts[0] != 'LOAD':
			continue
		if not is_hex(parts[1][2:]) or \
			not is_hex(parts[2][2:]) or \
			not is_hex(parts[4][2:]) or \
			not is_hex(parts[5][2:]):
			continue
		load_list.append((
			int(parts[1][2:], 16),
			int(parts[2][2:], 16),
			int(parts[4][2:], 16),
			int(parts[5][2:], 16)
			))

	if process.wait() != 0:
		raise Exception('process failed: readelf --program-headers')

	process = subprocess.Popen(["readelf", "--section-headers", "-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

	text_area = None
	init_addr = None
	init_array = None
	fini_addr = None
	fini_array = None
	for line in process.stdout:
		parts = line[6:].strip().split()
		if len(parts) < 5:
			continue

		if parts[0] == '.text':
			text_area = (int(parts[2], 16), int(parts[2], 16) + int(parts[4], 16))

		if parts[0] == '.init':
			init_addr = int(parts[2], 16)
		if parts[0] == '.fini':
			fini_addr = int(parts[2], 16)
		if parts[0] == '.init_array':
			init_array = (int(parts[2], 16), int(parts[2], 16) + int(parts[4], 16))
		if parts[0] == '.fini_array':
			fini_array = (int(parts[2], 16), int(parts[2], 16) + int(parts[4], 16))

	if process.wait() != 0:
		raise Exception('process failed: readelf --section-headers')

	registers = [	['%rax','%eax','%ax','%al'],
			['%rbx','%ebx','%bx','%bl'],
			['%rcx','%ecx','%cx','%cl'],
			['%rdx','%edx','%dx','%dl'],
			['%rsi','%esi','%si','%sil'],
			['%rdi','%edi','%di','%dil'],
			['%rbp','%ebp','%bp','%bpl'],
			['%rsp','%esp','%sp','%spl'],
			['%r8','%r8d','%r8w','%r8b'],
			['%r9','%r9d','%r9w','%r9b'],
			['%r10','%r10d','%r10w','%r10b'],
			['%r11','%r11d','%r11w','%r11b'],
			['%r12','%r12d','%r12w','%r12b'],
			['%r13','%r13d','%r13w','%r13b'],
			['%r14','%r14d','%r14w','%r14b'],
			['%r15','%r15d','%r15w','%r15b']	]

	#Below dict gives the mapping of register that has to be considered.For eg if group is 1 consider rbx
	main_register = {i: j[0] for i, j in enumerate(registers)}
	register_values = {i[0]: (None, 0) for i in registers}

	# List used to store address and callq functions along with retq
	func_list = []
	call_list = []
	syscall_list = []
	ret_list = []
	file_list = []

	binary = open(binary_name, 'rb')

	cmd = ["objdump", "-d", binary_name, "-j", ".text"]
	if init_addr:
		cmd += ["-j", ".init"]
	if fini_addr:
		cmd += ["-j", ".fini"]

	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=null_dev)

	linenbr = 0
	for line in process.stdout:
		line = line.strip()
		linenbr += 1
		if line == '' or linenbr < 7: # intial parts of objdump output don't care
			continue

		parts = line.split()

		if len(parts) == 2:
			if not is_hex(parts[0]):
				continue
			# start building class object , initialize new class object
			match = re.match(r"\<([A-Za-z0-9_]+)\>:$", parts[1])
			if match:
				# Filter name, may contain offset information, remove noise
				name = match.group(1)
				Caller.register_caller(func_list, int(parts[0], 16), name)
			continue

		result = re.match(r'([a-f0-9]+):$', parts[0])
		if not result:
			continue
		inst_addr = int(result.group(1), 16)

		# prepare function list
		# syscall no
		# store previous line in case of system calls
		# get values of mov instruction and keep in a variable

		# if instruction contains hints which start by #, filter it
		for i in range(len(parts)):
			if parts[i].startswith('#'):
				parts = parts[:i]
				break

		inst = None
		inst_size = 0
		for i in range(1, len(parts)):
			token = parts[i]
			if re.match('[a-f0-9][a-f0-9]$', token):
				inst_size += 1
				continue
			if token.startswith('mov') and i + 1 < len(parts):
				inst = token
				args = parts[i + 1].split(',')
				break
			if token.startswith('lea') and i + 1 < len(parts):
				inst = token
				args = parts[i + 1].split(',')
				break
			if token == 'xor' and i + 1 < len(parts):
				inst = token
				args = parts[i + 1].split(',')
				break
			if token == 'callq' or token == 'jmpq':
				inst = token
				args = []
				if i + 1 < len(parts):
					args.append(parts[i + 1])
				if i + 2 < len(parts):
					args.append(parts[i + 2])
				break
			if token == 'syscall' or token == 'sysenter':
				inst = 'syscall'
				break
			if token == 'int' and i + 1 < len(parts) and parts[i + 1] == '$0x50':
				inst = 'syscall'
				break
			if token == 'retq':
				ret_list.append(Inst(inst_addr))
				break

		if not inst:
			continue

		if inst.startswith('mov'):
			source = args[0]
			dest = args[1]
			s_reg = None
			d_reg = None
			for i in range(len(registers)):
				if source in registers[i]:
					s_reg = main_register[i]
				if dest in registers[i]:
					d_reg = main_register[i]

			if not d_reg: # memory write
				continue

			if source.startswith('$'): # direct assignment to reg
				source = source[1:]
				if source.startswith('0x'):
					if not is_hex(source[2:]):
						continue
					register_values[d_reg] = (int(source[2:], 16), inst_addr)
				else:
					register_values[d_reg] = (int(source), inst_addr)
				continue

			match = re.match(r'\((\%[^\)\+]+)\)', source)
			if match:
				for i in range(len(registers)):
					if match.group(1) in registers[i]:
						s_reg = main_register[i]
						break
				if s_reg and isinstance(register_values[s_reg][0], int) and register_values[s_reg][0] > 0:
					addr = register_values[s_reg][0]
					register_values[d_reg] = (0, inst_addr)
					for (fo, va, fsz, msz) in load_list:
						if addr >= va and addr < va + fsz:
							binary.seek(fo + (addr - va))
							register_values[d_reg] = \
								(struct.unpack('L', binary.read(8))[0], inst_addr);
							break
					continue
				s_reg = None

			match = re.match(r'\*?(-?)0x([a-f0-9]+)\(%rip\)$', source)
			if match:
				if match.group(1) == '-':
					addr = inst_addr + inst_size - int(match.group(2), 16)
				else:
					addr = inst_addr + inst_size + int(match.group(2), 16)
				register_values[d_reg] = (0, inst_addr)
				for (fo, va, fsz, msz) in load_list:
					if addr >= va and addr < va + fsz:
						binary.seek(fo + (addr - va))
						register_values[d_reg] = \
							(struct.unpack('L', binary.read(8))[0], inst_addr);
						break
				continue

			#if source_reg is not direct value ,rather register itself or mem location
			if s_reg:
				register_values[d_reg] = register_values[s_reg]
				continue

			register_values[d_reg] = (source, inst_addr)
			continue

		if inst == 'xor':
			source = args[0]
			dest = args[1]
			s_reg = None
			d_reg = None
			for i in range(len(registers)):
				if source in registers[i]:
					s_reg = main_register[i]
				if dest in registers[i]:
					d_reg = main_register[i]

			if s_reg == d_reg:
				register_values[d_reg] = (0, inst_addr)
			continue

		if inst.startswith('lea'):
			source = args[0]
			dest = args[1]
			s_reg = None
			d_reg = None
			for i in range(len(registers)):
				if source in registers[i]:
					s_reg = main_register[i]
				if dest in registers[i]:
					d_reg = main_register[i]

			# Indirect calls (*offset(%rip))
			match = re.match(r'\*?(-?)0x([a-f0-9]+)\(%rip\)$', args[0])
			if match:
				if match.group(1) == '-':
					addr = inst_addr + inst_size - int(match.group(2), 16)
				else:
					addr = inst_addr + inst_size + int(match.group(2), 16)

				if addr >= text_area[0] and addr < text_area[1]:
					Caller.register_caller(func_list, addr)
					call_list.append(Call_Inst(inst_addr, call_addr=addr))
					continue

				path = None
				for (fo, va, fsz, msz) in load_list:
					if addr >= va and addr < va + fsz:
						binary.seek(fo + (addr - va))
						ch = struct.unpack('s', binary.read(1))[0]
						addr += 1
						if ch == '/':
							path = ch
							while addr < va + fsz:
								ch = struct.unpack('s', binary.read(1))[0]
								addr += 1
								if ch == '\0' or ch in string.whitespace or ch == '\'' or ch == '\"':
									break
								if ch not in string.printable:
									path = None
									break
								path += ch
						break;
				if path:
					for prefix in File_Inst.prefixes:
						if path.startswith(prefix):
							file_list.append(File_Inst(inst_addr, path))

			continue

		if inst == 'callq' or inst == 'jmpq':
			match = re.match(r'(0x)?([a-f0-9]+)$', args[0])
			if match:
				func_addr = int(match.group(2), 16)
				func_name = None

				if len(args) == 1:
					compound = Vec_Syscall_Inst.get_compound(func_addr=func_addr)
					if compound:
						reg = register_values[compound['reg'][0]]
						if Vec_Syscall_Inst.is_valid(reg[0]):
							syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
						else:
							syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
						continue

					Caller.register_caller(func_list, func_addr)
					call_list.append(Call_Inst(inst_addr, call_addr=func_addr))
					continue


				# Direct call
				match = re.match(r"\<([a-zA-Z0-9_]+)(@plt)?(\+0x[a-f0-9]+)?\>$", args[1])
				if match:
					if not match.group(3):
						func_name = match.group(1)

					if func_name == 'syscall':
						rdi = register_values['%rdi']

						compound = Vec_Syscall_Inst.get_compound(syscall=rdi[0])
						if compound:
							reg = register_values[compound['reg'][1]]
							if Vec_Syscall_Inst.is_valid(reg[0]):
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
							else:
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
							continue

						if Syscall_Inst.is_valid(rdi[0]):
							syscall_list.append(Syscall_Inst(inst_addr, rdi[1], rdi[0]))
						else:
							syscall_list.append(Syscall_Inst(inst_addr, rdi[1], target=rdi[0]))
						continue

					if func_addr >= text_area[0] and func_addr < text_area[1]:
						Caller.register_caller(func_list, func_addr, func_name)
					else:
						func_addr = None

					compound = Vec_Syscall_Inst.get_compound(func_addr=func_addr, func_name=func_name)
					if compound:
						reg = register_values[compound['reg'][0]]
						if Vec_Syscall_Inst.is_valid(reg[0]):
							syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
						else:
							syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
						continue

					if func_addr or func_name:
						call_list.append(Call_Inst(inst_addr, call_addr=func_addr, call_name=func_name))
					else:
						call_list.append(Call_Inst(inst_addr, target=args[0]))
					continue

				# Indirect call (*ABS*+0x...@plt)
				match = re.match(r"\<\*ABS\*\+0x([a-f0-9]+)@plt\>$", args[1])
				if match:
					addr = match.group(1)
					if not is_hex(addr):
						continue
					func_addr = int(addr, 16)
					if func_addr in dynsym_list:
						func_name = dynsym_list[func_addr]

					if func_name == 'syscall':
						rdi = register_values['%rdi']

						compound = Vec_Syscall_Inst.get_compound(syscall=rdi[0])
						if compound:
							reg = register_values[compound['reg'][1]]
							if Vec_Syscall_Inst.is_valid(reg[0]):
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
							else:
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
							continue

						if isinstance(rdi[0], int):
							syscall_list.append(Syscall_Inst(inst_addr, rdi[1], rdi[0]))
						else:
							syscall_list.append(Syscall_Inst(inst_addr, rdi[1], target=rdi[0]))
						continue

				if func_addr >= text_area[0] and func_addr < text_area[1]:
					Caller.register_caller(func_list, func_addr)
				else:
					func_addr = None

				compound = Vec_Syscall_Inst.get_compound(func_addr=func_addr, func_name=func_name)
				if compound:
					reg = register_values[compound['reg'][0]]
					if Vec_Syscall_Inst.is_valid(reg[0]):
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
					else:
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
					continue

				if func_addr or func_name:
					call_list.append(Call_Inst(inst_addr, call_addr=func_addr, call_name=func_name))
				else:
					call_list.append(Call_Inst(inst_addr, target=args[0]))
				continue

			# Indirect calls (*offset(%rip))
			match = re.match(r'\*?(-?)0x([a-f0-9]+)\(%rip\)$', args[0])
			if match:
				if match.group(1) == '-':
					addr = inst_addr + inst_size - int(match.group(2), 16)
				else:
					addr = inst_addr + inst_size + int(match.group(2), 16)
				func_addr = None
				for (fo, va, fsz, msz) in load_list:
					if addr >= va and addr < va + fsz:
						binary.seek(fo + (addr - va))
						func_addr = struct.unpack('L', binary.read(8))[0]
						if func_addr < text_area[0] or func_addr >= text_area[1]:
							func_addr = None
						break
				if not func_addr:
					call_list.append(Call_Inst(inst_addr, target=args[0]))
					continue

				func_name = None
				if func_addr in dynsym_list.keys():
					func_name = dynsym_list[func_addr]
				else:
					Caller.register_caller(func_list, func_addr)
					func_name = func_addr

				compound = Vec_Syscall_Inst.get_compound(func_addr=func_addr, func_name=func_name)
				if compound:
					reg = register_values[compound['reg'][0]]
					if Vec_Syscall_Inst.is_valid(reg[0]):
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
					else:
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
					continue

				call_list.append(Call_Inst(inst_addr, call_addr=func_addr, call_name=func_name))

			call_list.append(Call_Inst(inst_addr, target=args[0]))
			continue

		if inst == 'syscall':
			rax = register_values['%rax']

			if Syscall_Inst.is_valid(rax[0]):
				compound = Vec_Syscall_Inst.get_compound(syscall=rax[0])
				if compound:
					reg = register_values[compound['reg'][0]]
					if Vec_Syscall_Inst.is_valid(reg[0]):
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req=reg[0]))
					else:
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=reg[1], req_target=reg[0]))
					continue

				syscall_list.append(Syscall_Inst(inst_addr, rax[1], rax[0]))
			else:
				syscall_list.append(Syscall_Inst(inst_addr, rax[1], target=rax[0]))
			continue

	if process.wait() != 0:
		raise Exception('process failed: objdump -d')

	if entry_addr:
		Caller.register_caller(func_list, entry_addr)

	if init_addr:
		Caller.register_caller(func_list, init_addr)
	if fini_addr:
		Caller.register_caller(func_list, fini_addr)

	if init_array:
		addr = init_array[0]
		Caller.register_caller(func_list, addr)
		while addr < init_array[1]:
			func_addr = None
			for (fo, va, fsz, msz) in load_list:
				if addr >= va and addr < va + fsz:
					binary.seek(fo + (addr - va))
					func_addr = struct.unpack('L', binary.read(8))[0]
					break;
			if func_addr:
				call_list.append(Call_Inst(addr, call_addr=func_addr))
				Caller.register_caller(func_list, func_addr)
			addr += 8

	if fini_array:
		addr = fini_array[0]
		Caller.register_caller(func_list, addr)
		while addr < fini_array[1]:
			func_addr = None
			for (fo, va, fsz, msz) in load_list:
				if addr >= va and addr < va + fsz:
					binary.seek(fo + (addr - va))
					func_addr = struct.unpack('L', binary.read(8))[0]
					break;
			if func_addr:
				call_list.append(Call_Inst(addr, call_addr=func_addr))
				Caller.register_caller(func_list, func_addr)
			addr += 8

	binary.close()

	def Caller_cmp(x, y):
		return cmp(x.func_addr, y.func_addr)

	func_list = sorted(func_list, Caller_cmp)

	def Inst_cmp(x, y):
		return cmp(x.inst_addr, y.inst_addr)

	call_list = sorted(call_list, Inst_cmp)
	syscall_list = sorted(syscall_list, Inst_cmp)
	file_list = sorted(file_list, Inst_cmp)

	func_iter = iter(func_list)
	call_iter = iter(call_list)
	syscall_iter = iter(syscall_list)
	file_iter = iter(file_list)
	ret_iter = iter(ret_list)

	def iter_next(iter):
		try:
			return next(iter)
		except StopIteration:
			return None

	next_func = iter_next(func_iter)
	next_call = iter_next(call_iter)
	next_syscall = iter_next(syscall_iter)
	next_file = iter_next(file_iter)
	next_ret = iter_next(ret_iter)
	while next_func:
		func = next_func
		next_func = iter_next(func_iter)

		while next_call:
			if next_func and next_call.inst_addr >= next_func.func_addr:
				break
			if next_call.call_addr:
				func.add_callees([next_call.call_addr])
			elif next_call.call_name:
				func.add_callees([next_call.call_name])
			else:
				func.add_callees(['<' + str(next_call.target) + '>'])
			next_call = iter_next(call_iter)

		while next_syscall:
			if next_func and next_syscall.inst_addr >= next_func.func_addr:
				break
			if next_syscall.assign < func.func_addr:
				next_syscall.syscall = -1
				next_syscall.target = '@%x' % next_syscall.inst_addr
			if next_syscall.syscall != -1:
				func.add_syscalls([next_syscall.syscall])

				if isinstance(next_syscall, Vec_Syscall_Inst):
					if next_syscall.req != -1:
						func.add_vecsyscalls([(next_syscall.syscall, next_syscall.req)])
					else:
						func.add_vecsyscalls([(next_syscall.syscall, '<' + str(next_syscall.req_target) + '>')])

			else:
				func.add_syscalls(['<' + next_syscall.target + '>'])
			next_syscall = iter_next(syscall_iter)

		while next_file:
			if next_func and next_file.inst_addr >= next_func.func_addr:
				break
			func.add_files([next_file.file])
			next_file = iter_next(file_iter)

		if next_func:
			while next_ret:
				if next_ret.inst_addr >= next_func.func_addr:
					break
				func.closed = True
				next_ret = iter_next(ret_iter)
		else:
			if next_ret:
				func.closed = True

	return func_list

class SymbolCaller:
	def __init__(self, name, callees, syscalls):
		self.name = name
		self.callees = callees
		self.traced_callees = set()
		self.syscalls = syscalls

	def __str__(self):
		result = '%s:' % (self.name)
		for c in self.callees:
			if isinstance(c, int):
				result += "\n\tcall: " + "%08x" % (c)
			else:
				result += "\n\tcall: " + c
		for s in self.syscalls:
			if isinstance(s, int) and s in syscall.syscalls:
				result += "\n\tsyscall: " + syscall.syscalls[s]
			else:
				result += "\n\tsyscall: " + str(s)
		return result

def get_callgraph_recursive(binary_name):
	calls = get_callgraph(binary_name)
	if not calls:
		return None

	symbols = get_symbols(binary_name)
	func_list = []
	for symbol in symbols:
		if not symbol.defined:
			continue

		for call in calls:
			if call.func_name and symbol.name == call.func_name:
				func_list.append(SymbolCaller(call.func_name, call.callees, call.syscalls))

	run = True
	while run:
		run = False
		for func in func_list:
			new_callees = set()
			for call in calls:
				if call.func_name:
					if call.func_name not in func.callees:
						continue
					new = call.func_name
				else:
					if call.func_addr not in func.callees:
						continue
					new = call.func_addr
				if new in func.callees or new in func.traced_callees:
					continue
				new_callees |= set([new])
				func.syscalls |= call.syscalls
			if new_callees:
				run = True
			func.traced_callees |= func.callees
			func.callees = new_callees

	for func in func_list:
		func.traced_callees |= func.callees
		func.callees = set()
		for symbol in symbols:
			if symbol.defined:
				continue

			if symbol.name in func.traced_callees:
				func.callees |= set([symbol.name])

		func.traced_callees = set()

	return func_list

def analysis_binary_call(sql, binary, pkg_id, bin_id):
	callers = get_callgraph(binary)
	calls = []
	unknown_calls = []
	apis = []
	unknown_apis = []

	for caller in callers:
		for callee in caller.callees:
			values = dict()
			values['func_addr'] = caller.func_addr

			if isinstance(callee, str) and callee.startswith('<'):
				values['target'] = callee[1:-1]
				unknown_calls.append(values)
				continue

			if isinstance(callee, str):
				values['call_name'] = callee
			else:
				values['call_addr'] = callee
			calls.append(values)

		for syscall in caller.syscalls:
			values = dict()
			values['func_addr'] = caller.func_addr

			if isinstance(syscall, int):
				values['api_type'] = linux_defs.SYSCALL
				values['api_id'] = syscall
				apis.append(values)
				continue

			if isinstance(syscall, str):
				values['target'] = syscall[1:-1]
			else:
				values['target'] = ''
			unknown_apis.append(values)

		for syscall in caller.vecsyscalls:
			for request in caller.vecsyscalls[syscall]:
				values = dict()
				values['func_addr'] = caller.func_addr

				if syscall == linux_defs.FCNTL_SYSCALL:
					values['api_type'] = linux_defs.FCNTL
				if syscall == linux_defs.IOCTL_SYSCALL:
					values['api_type'] = linux_defs.IOCTL
				if syscall == linux_defs.PRCTL_SYSCALL:
					values['api_type'] = linux_defs.PRCTL

				if isinstance(request, int) or isinstance(request, long):
					values['api_id'] = request
					apis.append(values)
					continue

				if isinstance(request, str):
					values['target'] = request[1:-1]
				else:
					values['target'] = ''
				unknown_apis.append(values)

		for file in caller.files:
			values = dict()
			values['func_addr'] = caller.func_addr
			values['api_type'] = linux_defs.PSEUDOFILE
			values['api_id'] = sql.hash_text(file)
			values['api_name'] = file
			apis.append(values)

	for values in apis:
		if 'api_name' in values:
			os_target.append_api_list(sql, values['api_type'], values['api_id'], values['api_name'])

	condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
	condition_unknown = condition + ' and known=False'
	sql.delete_record(tables['binary_call'], condition)
	sql.delete_record(tables['binary_call_unknown'], condition_unknown)
	sql.delete_record(tables['binary_api_usage'], condition)
	sql.delete_record(tables['binary_api_usage_unknown'], condition_unknown)

	for values in calls:
		values['pkg_id'] = pkg_id
		values['bin_id'] = bin_id
		sql.append_record(tables['binary_call'], values)

	for values in unknown_calls:
		values['pkg_id'] = pkg_id
		values['bin_id'] = bin_id
		sql.append_record(tables['binary_call_unknown'], values)

	for values in apis:
		values['pkg_id'] = pkg_id
		values['bin_id'] = bin_id
		sql.append_record(tables['binary_api_usage'], values)

	for values in unknown_apis:
		values['pkg_id'] = pkg_id
		values['bin_id'] = bin_id
		sql.append_record(tables['binary_api_usage_unknown'], values)

if __name__ == "__main__":
	if sys.argv[1] == '-r':
		for caller in get_callgraph_recursive(sys.argv[2]):
			print caller

		print "File Access:"
		for file in get_fileaccess(sys.argv[2]):
			print '\t' + file
	else:
		for caller in get_callgraph(sys.argv[1]):
			print caller

		print "File Access:"
		for file in get_fileaccess(sys.argv[1]):
			print '\t' + file
