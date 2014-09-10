#!/usr/bin/python

import os
import sys
import re
import subprocess

def prepare_syscalls():
	res = {}
	with open("systable.h", "r") as text:
		for line in text:
			value, key = line.split()
			res[key] = value
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
		if callees:
			caller.callees = caller.callees|set(callees)
		if syscalls:
			caller.syscalls = caller.syscalls|set(syscalls)

	def __str__(self):
		return '%08x: %s' % (self.func_addr, self.func_name)

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
		match = re.match(r"([A-Za-z0-9_]+)@[A-Za-z0-9_]+", parts[7])
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
			match = re.match(r"\<([A-Za-z0-9_]+)\>:", parts[1])
			if match:
				# Filter name, may contain offset information, remove noise
				name = match.group(1)
				Caller.register_caller(func_list, int(parts[0], 16), name)
			continue

		result = re.search(r'([a-f0-9]+):', parts[0])
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
		for i in range(len(parts)):
			token = parts[i]
			if token.startswith('mov') and i + 1 < len(parts):
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

		if inst == 'callq':
			if re.match(r'[a-f0-9]+', args[0]):
				func_addr = int(args[0], 16)

				# Direct call
				match = re.match(r"\<([a-zA-Z0-9_]+)(@plt)?\>", args[1])
				if match:
					func_name = match.group(1)
					call_list.append(Call_Inst(inst_addr, func_name))
					continue

				# Indirect call (*ABS*+0x...@plt)
				match = re.match(r"\<\*ABS\*+0x([a-f0-9]+)@plt\>", args[1])
				if match:
					addr = match.group(1)
					func_name = dynsym_list[addr]
					call_list.append(Call_Inst(inst_addr, func_name))
					continue

				Caller.register_caller(func_list, func_addr)
				call_list.append(Call_Inst(inst_addr, func_addr))
				continue

			# Indirect calls (*offset(%rip))
			match = re.match(r'\*?0x([a-f0-9]+)\(%rip\)', args[0])
			if match:
				addr = inst_addr + int(match.group(0), 16)
				func_addr = None
				for (fo, va, fsz, msz) in load_list:
					if addr >= va and addr < va + fsz:
						binary.seek(fo + (addr - va))
						func_addr = struct.unpack('i', binary.read(16))[0]
						break
				Caller.register_caller(func_list, func_addr)
				call_list.append(Call_Inst(inst_addr, func_addr))
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

	# print the call graph
	for call in call_list:
		print call
	for syscall in syscall_list:
		print syscall
	for caller in func_list:
		print caller

if __name__ == "__main__":
	get_callgraph(sys.argv[1])
