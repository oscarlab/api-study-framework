#!/usr/bin/python

from task import Task
import package
from sql import Table

import os
import sys
import re
import subprocess

def prepare_syscalls():
	res = {}
	with open("systable.h", "r") as text:
		for line in text:
			value, key = line.split()
			res[int(key)] = value
	return res

syscalls_info = prepare_syscalls()

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
		self.closed = False

	def add_callees(self, callees):
		if callees:
			self.callees = self.callees|set(callees)

	def add_syscalls(self, syscalls):
		if syscalls:
			self.syscalls = self.syscalls|set(syscalls)

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
			if isinstance(s, int):
				result += "\n\tsyscall: " + syscalls_info[s]
			else:
				result += "\n\tsyscall: " + s
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
	def __init__(self, inst_addr, call_target):
		Inst.__init__(self, inst_addr)
		self.call_target = call_target

	def __str__(self):
		if isinstance(self.call_target, str):
			return Inst.__str__(self) + ' call ' + self.call_target
		else:
			return Inst.__str__(self) + ' call 0x%08x' % (self.call_target)

class Syscall_Inst(Inst):
	def __init__(self, inst_addr, syscall_no):
		Inst.__init__(self, inst_addr)
		self.syscall_no = syscall_no

	def __str__(self):
		if isinstance(self.syscall_no, str):
			return Inst.__str__(self) + ' syscall ' + self.syscall_no
		else:
			return Inst.__str__(self) + ' syscall %d' % (self.syscall_no)

def get_callgraph(binaryname):
	process = subprocess.Popen(["readelf", "--dyn-syms","-W", binaryname],
			stdout=subprocess.PIPE
			)

	dynsym_list = {}
	for line in process.stdout:
		parts = line.strip().split()
		if len(parts) < 8:
			continue
		if not is_hex(parts[1]):
			continue
		match = re.match(r"([A-Za-z0-9_]+)@[A-Za-z0-9_]+$", parts[7])
		if not match:
			continue
		dynsym_list[int(parts[1], 16)] = match.group(1)

	process = subprocess.Popen(["readelf", "--program-headers", "-W", binaryname],
			stdout=subprocess.PIPE
			)

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

	process = subprocess.Popen(["readelf", "--section-headers", "-W", binaryname],
			stdout=subprocess.PIPE
			)

	text_area = None
	for line in process.stdout:
		parts = line.strip().split()
		if len(parts) < 6:
			continue
		if parts[1] != '.text':
			continue
		if not is_hex(parts[3]) or not is_hex(parts[5]):
			break
		text_area = (int(parts[3], 16), int(parts[3], 16) + int(parts[5], 16))

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
	register_values = {i[0]: None for i in registers}

	# List used to store address and callq functions along with retq
	func_list = []
	call_list = []
	syscall_list = []
	ret_list = []

	binary = open(binaryname, 'rb')

	process = subprocess.Popen(["objdump", "-d", binaryname, "-j", ".text"],
			stdout=subprocess.PIPE
			)

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
			if token == 'callq' and i + 2 < len(parts):
				inst = token
				args = [parts[i + 1], parts[i + 2]]
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
					register_values[d_reg] = int(source[2:], 16)
				else:
					register_values[d_reg] = int(source)
				continue

			#if source_reg is not direct value ,rather register itself or mem location
			if s_reg:
				register_values[d_reg] = register_values[s_reg]
				continue

			register_values[d_reg] = source
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
				register_values[d_reg] = 0
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
					call_list.append(Call_Inst(inst_addr, addr))
			continue

		if inst == 'callq':
			if re.match(r'[a-f0-9]+$', args[0]):
				func_addr = int(args[0], 16)

				# Direct call
				match = re.match(r"\<([a-zA-Z0-9_]+)(@plt)?(\+0x[a-f0-9]+)?\>$", args[1])
				if match:
					if match.group(3):
						Caller.register_caller(func_list, func_addr)
						call_list.append(Call_Inst(inst_addr, func_addr))
					else:
						func_name = match.group(1)
						call_list.append(Call_Inst(inst_addr, func_name))
					continue

				# Indirect call (*ABS*+0x...@plt)
				match = re.match(r"\<\*ABS\*+0x([a-f0-9]+)@plt\>$", args[1])
				if match:
					addr = match.group(1)
					func_name = dynsym_list[addr]
					call_list.append(Call_Inst(inst_addr, func_name))
					continue

				Caller.register_caller(func_list, func_addr)
				call_list.append(Call_Inst(inst_addr, func_addr))
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
						func_addr = struct.unpack('i', binary.read(16))[0]
						break
				func_name = None
				if func_addr in dynsym_list.keys():
					func_name = dynsym_list[func_addr]
				else:
					Caller.register_caller(func_list, func_addr)
				call_list.append(Call_Inst(inst_addr, func_addr, func_name))
			continue

		if inst == 'syscall':
			syscall_list.append(Syscall_Inst(inst_addr, register_values['%rax']))
			continue

	def Caller_cmp(x, y):
		return x.func_addr - y.func_addr

	func_list = sorted(func_list, Caller_cmp)

	def Inst_cmp(x, y):
		return x.inst_addr - y.inst_addr

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
			func.add_callees([next_call.call_target])
			next_call = iter_next(call_iter)

		while next_syscall:
			if next_func and next_syscall.inst_addr >= next_func.func_addr:
				break
			func.add_syscalls([next_syscall.syscall_no])
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

binary_call_table = Table('binary_call', [
			('binary', 'TEXT', 'NOT NULL'),
			('func', 'TEXT', 'NOT NULL'),
			('target', 'TEXT', 'NOT NULL')],
			['binary', 'func', 'target'])

binary_syscall_table = Table('binary_syscall', [
			('binary', 'TEXT', 'NOT NULL'),
			('func', 'TEXT', 'NOT NULL'),
			('syscall', 'INTEGER', ''),
			('source', 'TEXT', '')],
			['binary', 'func', 'syscall', 'source'])

def BinaryCallgraph_run(jmgr, sql, args):
	sql.connect_table(binary_call_table)
	sql.connect_table(binary_syscall_table)
	pkgname = args[0]
	bin = args[1]
	dir = args[2]
	if not dir:
		(dir, pkgname, version) = package.unpack_package(args[0])
		if not dir:
			return
	if len(args) > 3:
		ref = args[3]
	else:
		ref = None
	path = dir + '/' + bin
	if os.path.exists(path):
		callers = get_callgraph(path)
		for caller in callers:
			for callee in caller.callees:
				values = dict()
				values['binary'] = bin
				if caller.func_name:
					values['func'] = caller.func_name
				else:
					values['func'] = '0x%08x' % (caller.func_addr)
				if isinstance(callee, int):
					values['target'] = '0x%08x' % (callee)
				else:
					values['target'] = callee

				sql.append_record(binary_call_table, values)

			for syscall in caller.syscalls:
				values = dict()
				values['binary'] = bin
				if caller.func_name:
					values['func'] = caller.func_name
				else:
					values['func'] = '0x%08x' % (caller.func_addr)
				if isinstance(syscall, int):
					values['syscall'] = syscall
					values['source'] = ''
				else:
					values['syscall'] = -1
					values['source'] = syscall

				sql.append_record(binary_syscall_table, values)
	sql.commit()
	if ref:
		if not package.dereference_dir(dir, ref):
			return
	shutil.rmtree(dir)

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
		shutil.rmtree(dir)
		return
	for (bin, type) in binaries:
		ref = package.reference_dir(dir)
		BinaryCallgraph.create_job(jmgr, [pkgname, bin, dir, ref])

def BinaryCallInfo_job_name(args):
	return "Binary Call Info: " + args[0]

BinaryCallInfo = Task(
	name="Binary Call Info",
	func=BinaryCallInfo_run,
	arg_defs=["Package Name"],
	job_name=BinaryCallInfo_job_name)

if __name__ == "__main__":
	for caller in get_callgraph(sys.argv[1]):
		print caller
