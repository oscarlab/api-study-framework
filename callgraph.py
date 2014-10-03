#!/usr/bin/python

from task import Task
import package
from sql import Table
import syscall
from symbol import get_symbols
from binary import get_binary_id, update_binary_callgraph
import main

import os
import sys
import re
import subprocess
import struct

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
		self.target = target

	def __str__(self):
		if self.syscall != -1:
			return Inst.__str__(self) + ' syscall ' + str(self.syscall)

		return Inst.__str__(self) + ' syscall ' + self.target

class Vec_Syscall_Inst(Syscall_Inst):
	syscalls = [
		{'syscall':  16, 'func_addr': 0, 'func_name':  'ioctl', 'reg': ('%rsi', '%rdx')},
		{'syscall':  72, 'func_addr': 0, 'func_name':  'fcntl', 'reg': ('%rsi', '%rdx')},
		{'syscall': 157, 'func_addr': 0, 'func_name':  'prctl', 'reg': ('%rdi', '%rsi')},
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

	def __init__(self, inst_addr, assign=None, syscall=-1, target='', req_assign=None, req=-1, req_target=''):
		Syscall_Inst.__init__(self, inst_addr, assign, syscall, target)
		self.req_assign = req_assign
		self.req = req
		self.req_target = req_target

	def __str__(self):
		if self.req != -1:
			return 'compound ' + Syscall_Inst.__str__(self) + ' by ' + str(self.req)

		return 'compound ' + Syscall_Inst.__str__(self) + ' by ' + self.req_target

def get_callgraph(binary_name):
	process = subprocess.Popen(["readelf", "--file-header","-W", binary_name], stdout=subprocess.PIPE, stderr=main.null_dev)

	class_name = 'ELF64'
	entry_addr = None
	for line in process.stdout:
		results = re.match(r"([^\:]+)\: +(.+)", line.strip())
		if results:
			key = results.group(1)
			val = results.group(2)
			if key == 'Class':
				class_name = val
			if key == 'Entry point address':
				entry_addr = int(val[2:], 16)

	if process.wait() != 0:
		raise Exception('process failed: readelf --file-header')

	if class_name != 'ELF64':
		raise Exception('Unsupported class: ' + class_name);

	process = subprocess.Popen(["readelf", "--dyn-syms","-W", binary_name], stdout=subprocess.PIPE, stderr=main.null_dev)

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

	process = subprocess.Popen(["readelf", "--program-headers", "-W", binary_name], stdout=subprocess.PIPE, stderr=main.null_dev)

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

	process = subprocess.Popen(["readelf", "--section-headers", "-W", binary_name], stdout=subprocess.PIPE, stderr=main.null_dev)

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

	binary = open(binary_name, 'rb')

	cmd = ["objdump", "-d", binary_name, "-j", ".text"]
	if init_addr:
		cmd += ["-j", ".init"]
	if fini_addr:
		cmd += ["-j", ".fini"]

	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=main.null_dev)

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
			if token == 'callq':
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

		if inst == 'callq':
			if re.match(r'[a-f0-9]+$', args[0]):
				func_addr = int(args[0], 16)
				func_name = None

				# Direct call
				match = re.match(r"\<([a-zA-Z0-9_]+)(@plt)?(\+0x[a-f0-9]+)?\>$", args[1])
				if match:
					if not match.group(3):
						func_name = match.group(1)

					if func_name == 'syscall':
						rdi = register_values['%rdi']

						compound = Vec_Syscall_Inst.get_compound(syscall=rdi[0])
						if compound:
							req = register_values[compound['reg'][1]]
							if isinstance(req[0], int) or isinstance(reg[0], long):
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req=req[0]))
							else:
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req_target=req[0]))
							continue

						if isinstance(rdi[0], int):
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
						req = register_values[compound['reg'][0]]
						if isinstance(req[0], int) or isinstance(req[0], long):
							syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req=req[0]))
						else:
							syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req_target=req[0]))
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
							req = register_values[compound['reg'][1]]
							if isinstance(req[0], int) or isinstance(req[0], long):
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req=req[0]))
							else:
								syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req_target=req[0]))
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
					req = register_values[compound['reg'][0]]
					if isinstance(req[0], int) or isinstance(req[0], long):
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req=req[0]))
					else:
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req_target=req[0]))
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
					req = register_values[compound['reg'][0]]
					if isinstance(req[0], int) or isinstance(req[0], long):
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req=req[0]))
					else:
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req_target=req[0]))
					continue

				call_list.append(Call_Inst(inst_addr, call_addr=func_addr, call_name=func_name))

			call_list.append(Call_Inst(inst_addr, target=args[0]))
			continue

		if inst == 'syscall':
			rax = register_values['%rax']

			if isinstance(rax[0], int):
				compound = Vec_Syscall_Inst.get_compound(syscall=rax[0])
				if compound:
					req = register_values[compound['reg'][0]]
					if isinstance(req[0], int) or isinstance(req[0], long):
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req=req[0]))
					else:
						syscall_list.append(Vec_Syscall_Inst(inst_addr, inst_addr, compound['syscall'], req_assign=req[1], req_target=req[0]))
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

	func_iter = iter(func_list)
	call_iter = iter(call_list)
	syscall_iter = iter(syscall_list)
	ret_iter = iter(ret_list)

	def iter_next(iter):
		try:
			return next(iter)
		except StopIteration:
			return None

	next_func = iter_next(func_iter)
	next_call = iter_next(call_iter)
	next_syscall = iter_next(syscall_iter)
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
				func.add_callees(['<' + next_call.target + '>'])
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
						func.add_vecsyscalls([(next_syscall.syscall, '<' + next_syscall.req_target + '>')])

			else:
				func.add_syscalls(['<' + next_syscall.target + '>'])
			next_syscall = iter_next(syscall_iter)

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

binary_call_table = Table('binary_call', [
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('call_addr', 'INT', ''),
			('call_name', 'VARCHAR', '')])

binary_unknown_call_table = Table('binary_unknown_call', [
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('call_addr', 'INT', ''),
			('call_name', 'VARCHAR', '')],
			['bin_id', 'func_addr', 'target'])

binary_syscall_table = Table('binary_syscall', [
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('syscall', 'SMALLINT', 'NOT NULL')])

binary_unknown_syscall_table = Table('binary_unknown_syscall', [
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('syscall', 'SMALLINT', '')],
			['bin_id', 'func_addr', 'target'])

binary_vecsyscall_table = Table('binary_vecsyscall', [
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('syscall', 'SMALLINT', 'NOT NULL'),
			('request', 'BIGINT', 'NOT NULL')])

binary_unknown_vecsyscall_table = Table('binary_unknown_vecsyscall', [
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('syscall', 'SMALLINT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('request', 'BIGINT', '')],
			['bin_id', 'func_addr', 'syscall', 'target'])

def BinaryCallgraph_run(jmgr, sql, args):
	sql.connect_table(binary_call_table)
	sql.connect_table(binary_unknown_call_table)
	sql.connect_table(binary_syscall_table)
	sql.connect_table(binary_unknown_syscall_table)
	sql.connect_table(binary_vecsyscall_table)
	sql.connect_table(binary_unknown_vecsyscall_table)

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
		(dir, pkgname, version) = package.unpack_package(args[0])
		if not dir:
			return
		unpacked = True

	exc = None
	try:
		path = dir + '/' + bin
		bin_id = get_binary_id(sql, bin)
		condition = 'bin_id=\'' + str(bin_id) + '\''
		sql.delete_record(binary_call_table, condition)
		sql.delete_record(binary_syscall_table, condition)
		sql.delete_record(binary_vecsyscall_table, condition)
		if os.path.exists(path):
			callers = get_callgraph(path)
			for caller in callers:
				for callee in caller.callees:
					values = dict()
					values['bin_id'] = bin_id
					values['func_addr'] = caller.func_addr

					if isinstance(callee, str) and callee.startswith('<'):
						values['target'] = callee[1:-1]
						try:
							sql.append_record(binary_unknown_call_table, values)
						except:
							pass
						continue

					if isinstance(callee, str):
						values['call_name'] = callee
					else:
						values['call_addr'] = callee

					sql.append_record(binary_call_table, values)

				for syscall in caller.syscalls:
					values = dict()
					values['bin_id'] = bin_id
					values['func_addr'] = caller.func_addr

					if isinstance(syscall, int) and syscall >= 0 and syscall < 400:
						values['syscall'] = syscall
						sql.append_record(binary_syscall_table, values)
						continue

					if isinstance(syscall, str):
						values['target'] = syscall[1:-1]
					else:
						values['target'] = ''
					try:
						sql.append_record(binary_unknown_syscall_table, values)
					except:
						pass

				for syscall in caller.vecsyscalls:
					for request in caller.vecsyscalls[syscall]:
						values = dict()
						values['bin_id'] = bin_id
						values['func_addr'] = caller.func_addr
						values['syscall'] = syscall

						if isinstance(request, int) or isinstance(request, long):
							values['request'] = request
							sql.append_record(binary_vecsyscall_table, values)
							continue

						if isinstance(request, str):
							values['target'] = request[1:-1]
						else:
							values['target'] = ''
						try:
							sql.append_record(binary_unknown_vecsyscall_table, values)
						except:
							pass

		update_binary_callgraph(sql, bin_id)
		sql.commit()
	except Exception as err:
		exc = sys.exc_info()

	if (ref and package.dereference_dir(dir, ref)) or unpacked:
		package.remove_dir(dir)
	if exc:
		raise exc[1], None, exc[2]

def BinaryCallgraph_job_name(args):
	return "Binary Callgraph: " + args[1] + " in " + args[0]

BinaryCallgraph = Task(
	name="Binary Callgraph",
	func=BinaryCallgraph_run,
	arg_defs=["Package Name", "Binary Path", "Unpack Path"],
	job_name=BinaryCallgraph_job_name)

def BinaryCallInfo_run(jmgr, sql, args):
	(dir, pkgname, version) = package.unpack_package(args[0])
	if not dir:
		return
	binaries = package.walk_package(dir)
	if not binaries:
		package.remove_dir(dir)
		return
	for (bin, type) in binaries:
		if type == 'lnk':
			continue
		ref = package.reference_dir(dir)
		BinaryCallgraph.create_job(jmgr, [pkgname, bin, dir, ref])

def BinaryCallInfo_job_name(args):
	return "Binary Call Info: " + args[0]

BinaryCallInfo = Task(
	name="Binary Call Info",
	func=BinaryCallInfo_run,
	arg_defs=["Package Name"],
	job_name=BinaryCallInfo_job_name)

def BinaryCallInfoByNames_run(jmgr, sql, args):
	packages = package.get_packages_by_names(args[0].split())
	if packages:
		for i in packages:
			BinaryCallInfo.create_job(jmgr, [i])

def BinaryCallInfoByNames_job_name(args):
	return "Binary Call Info By Names: " + args[0]

BinaryCallInfoByNames = Task(
	name="Binary Call Info By Names",
	func=BinaryCallInfoByNames_run,
	arg_defs=["Package Names"],
	job_name=BinaryCallInfoByNames_job_name)

def BinaryCallInfoByPrefixes_run(jmgr, sql, args):
	packages = package.get_packages_by_prefixes(args[0].split())
	if packages:
		for i in packages:
			BinaryCallInfo.create_job(jmgr, [i])

def BinaryCallInfoByPrefixes_job_name(args):
	return "Binary Call Info By Prefixes: " + args[0]

BinaryCallInfoByPrefixes = Task(
	name="Binary Call Info By Prefixes",
	func=BinaryCallInfoByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=BinaryCallInfoByPrefixes_job_name)

def BinaryCallInfoByRanks_run(jmgr, sql, args):
	packages = package.get_packages_by_ranks(sql, int(args[0]), int(args[1]))
	if packages:
		for i in packages:
			BinaryCallInfo.create_job(jmgr, [i])

def BinaryCallInfoByRanks_job_name(args):
	return "Binary Call Info By Ranks: " + args[0] + " to " + args[1]

BinaryCallInfoByRanks = Task(
	name="Binary Call Info By Ranks",
	func=BinaryCallInfoByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=BinaryCallInfoByRanks_job_name)

if __name__ == "__main__":
	if sys.argv[1] == '-r':
		for caller in get_callgraph_recursive(sys.argv[2]):
			print caller
	else:
		for caller in get_callgraph(sys.argv[1]):
			print caller
