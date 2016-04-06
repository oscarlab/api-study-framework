#!/usr/bin/python

from task import Task
import package
from sql import Table
import syscall
from symbol import get_symbols
from id import get_path_id, get_path, get_pkgname_id, get_pkgname, get_pkgnames_by_prefix
from package_popularity import get_packages_by_ranks
import main

import os
import sys
import re
import subprocess
import struct
import string
from sets import Set

sys.path.append('pybfd/lib/python')
from pybfd import opcodes, bfd
from pybfd.opcodes import Opcodes, OpcodesException
from pybfd.bfd import Bfd, BfdException

x86_64_regs = [
		['rax',  'eax',  'ax',   'al'  ],
		['rbx',  'ebx',  'bx',   'bl'  ],
		['rcx',  'ecx',  'cx',   'cl'  ],
		['rdx',  'edx',  'dx',   'dl'  ],
		['rsi',  'esi',  'si',   'sil' ],
		['rdi',  'edi',  'di',   'dil' ],
		['rbp',  'ebp',  'bp',   'bpl' ],
		['rsp',  'esp',  'sp',   'spl' ],
		['r8',   'r8d',  'r8w',  'r8b' ],
		['r9',   'r9d',  'r9w',  'r9b' ],
		['r10',  'r10d', 'r10w', 'r10b'],
		['r11',  'r11d', 'r11w', 'r11b'],
		['r12',  'r12d', 'r12w', 'r12b'],
		['r13',  'r13d', 'r13w', 'r13b'],
		['r14',  'r14d', 'r14w', 'r14b'],
		['r15',  'r15d', 'r15w', 'r15b']]

i386_regs = [
		['eax',  'ax',   'al'  ],
		['ebx',  'bx',   'bl'  ],
		['ecx',  'cx',   'cl'  ],
		['edx',  'dx',   'dl'  ],
		['esi',  'si',   'sil' ],
		['edi',  'di',   'dil' ],
		['ebp',  'bp',   'bpl' ],
		['esp',  'sp',   'spl' ]]

def ishex(str):
	return str.startswith('0x')

def hex2int(str):
	return int(str[2:], 16)

class Register:
	def __init__(self, names):
		self.names = names
		self.masks = []
		self.sizes = []
		mask = 256
		size = 1
		for n in names[::-1]:
			self.masks.append(mask - 1)
			self.sizes.append(size)
			mask = mask * mask
			size = size + size

	def index_reg(self, regname):
		i = 0
		while i < len(self.names):
			if regname == self.names[i]:
				return (self.sizes[i], self.masks[i])
			i += 1
		return (None, None)

class RegisterSet:
	def __init__(self, regs):
		self.regs = [Register(reg) for reg in regs]

	def is_reg(self, name):
		for reg in self.regs:
			if name in reg.names:
				return True
		return False

	def index_reg(self, regname):
		for reg in self.regs:
			(size, mask) = reg.index_reg(regname)
			if size is not None:
				return (reg, size, mask)
		return (None, None, Nonae)

class Inst:
	def __init__(self, bb, addr, dism):
		self.bblock = bb
		self.addr = addr
		self.dism = dism

class InstCall(Inst):
	def __init__(self, bb, addr, dism, targets):
		Inst.__init__(self, bb, addr, dism)
		self.targets = targets

class InstSyscall(Inst):
	def __init__(self, bb, addr, dism):
		Inst.__init__(self, bb, addr, dism)

class BBlock:
	def __init__(self, start, end=None):
		self.start = start
		self.end = end
		self.insts = []
		self.targets = Set()

class Func:
	def __init__(self, entry):
		self.entry = entry
		self.bblocks = []
		self.new_bblocks = []

	def add_bblock(self, addr):
		closest = None
		for bb in self.bblocks + self.new_bblocks:
			if addr == bb.start:
				return bb

			if bb.end:
				if addr > bb.start and addr < bb.end:
					new = BBlock(addr, bb.end)
					bb.end = addr

					splice = 0
					for inst in bb.insts:
						if inst.addr >= addr:
							break
						splice += 1

					new.insts = bb.insts[splice:]
					bb.insts = bb.insts[:splice]
					self.bblocks.append(new)
					return new
			else:
				bb.end = addr

			if bb.start > addr and (closest is None or closest > bb.start):
				closest = bb.start

		new = BBlock(addr, closest)
		self.new_bblocks.append(new)
		return new

class Op:
	def __init__(self, val=None):
		self.val = None

	def get_val(self, regval):
		return self.val

class OpReg(Op):
	def __init__(self, reg, mask):
		Op.__init__(self)
		self.reg = reg
		self.mask = mask

	def get_val(self, regval):
		if isinstance(regval[self.reg], (int, long)):
			return regval[self.reg] & self.mask
		else:
			return None

class OpArith(Op):
	ADD = 0
	SUB = 1
	MUL = 2
	DIV = 3

	def __init__(self, op1, op2, arith):
		Op.__init__(self)
		self.op1 = op1
		self.op2 = op2
		self.arith = arith

	def get_val(self, regval):
		val1 = self.op1.get_val(regval)
		val2 = self.op2.get_val(regval)
		if val1 and val2:
			if self.arith == ADD:
				return val1 + val2
			elif self.arith == SUB:
				return val1 - val2
			elif self.arith == MUL:
				return val1 * val2
			elif self.arith == DIV:
				return val1 / val2
		return None

class OpLoad(Op):
	def __init__(self, addr, size):
		Op.__init__(self)
		self.addr = addr
		self.size = size

	def get_val(self, regval):
		return None

def get_callgraph(binary_name):

	# Initialize BFD instance
	bfd = Bfd(binary_name)

	if bfd.target == 'elf64-x86-64':
		ptr_fmt = '<Q'
		ptr_size = 8
	elif bfd.target == 'elf32-i386':
		ptr_fmt = '<L'
		ptr_size = 4
	else:
		return

	entry_addr = bfd.start_address
	dynsyms = bfd.symbols

	if '.text' in bfd.sections:
		text_area = (bfd.sections['.text'].vma,
			     bfd.sections['.text'].vma + bfd.sections['.text'].size,
			     bfd.sections['.text'].file_offset)
	else:
		# must have text section
		return

	if '.data' in bfd.sections:
		data_area = (bfd.sections['.data'].vma,
			     bfd.sections['.data'].vma + bfd.sections['.data'].size,
			     bfd.sections['.data'].file_offset)
	else:
		# must have data section
		return

	if '.init' in bfd.sections:
		init_addr = bfd.sections['.init'].ptr
	else:
		init_addr = None

	if '.init_array' in bfd.sections:
		init_area = (bfd.sections['.init_array'].vma,
			     bfd.sections['.init_array'].vma + bfd.sections['.init_array'].size,
			     bfd.sections['.init_array'].file_offset)
	else:
		init_area = None

	if '.fini' in bfd.sections:
		fini_addr = bfd.sections['.fini'].ptr
	else:
		fini_addr = None

	if '.fini_array' in bfd.sections:
		fini_area = (bfd.sections['.fini_array'].vma,
			     bfd.sections['.fini_array'].vma + bfd.sections['.fini_array'].size,
			     bfd.sections['.fini_array'].file_offset)
	else:
		fini_area = None

	class CodeOpcodes(Opcodes):
		def __init__(self, bfd, start, end):
			Opcodes.__init__(self, bfd)

			if bfd.target == 'elf64-x86-64':
				self.regset = RegisterSet(x86_64_regs)
			elif bfd.target == 'elf32-i386':
				self.regset = RegisterSet(i386_regs)

			self.start = start
			self.end = end
			self.entries = []
			self.funcs = []
			self.cur_func = None
			self.cur_bb = None
			self.nfuncs = 0
			self.nbblocks = 0

		def add_entry(self, addr):
			if self.cur_func and self.cur_func.entry == addr:
				return

			if addr < self.start or addr > self.end:
				return

			if addr in self.entries:
				return

			for func in self.funcs:
				if addr == func.entry:
					return

			self.entries.append(addr)

		def process_instructions(self, address, size, branch_delay_insn,
			insn_type, target, target2, disassembly):

			regex = r'^(?P<repz>repz )?(?P<insn>\S+)(\s+(?P<arg1>[^,]+)(,(?P<arg2>[^#]+)(#(?P<comm>.+))?)?)?$'
			m = re.match(regex, disassembly)

			if not m:
				return opcodes.PYBFD_DISASM_CONTINUE

			repz = (m.group('repz') is not None)
			insn = m.group('insn')
			arg1 = m.group('arg1')
			arg2 = m.group('arg2')
			comm = m.group('comm')

			def match_addr(arg):
				regex = r'^(?P<load>(?P<size>QWORD|DWORD|WORD|BYTE) PTR )?\[(?P<addr>[^\]]+)\]$'
				m = re.match(regex, arg)
				if m:
					addr = m.group('addr')
					if m.group('load'):
						size = m.group('size')
						if size == 'QWORD':
							return (addr, 8)
						elif size == 'DWORD':
							return (addr, 4)
						elif size == 'WORD':
							return (addr, 2)
						else:
							return (addr, 1)
					else:
						return (addr, None)
				else:
					return (None, None)

			def match_rip(arg, addr, size):
				regex = r'^rip\+(?P<offset>0x[0-9a-f]+)$'
				m = re.match(regex, arg)
				if m:
					return addr + size + hex2int(m.group('offset'))
				return None

			def match_fmt(arg, regset):
				regex = r'^(?P<base>[a-z0-9]+(?=(\+|-|$)))?(\+(?=[a-z0-9]))?((?P<reg>[a-z0-9]+)\*(?P<scale>1|2|4|8))?((?P<arith>\+|-)(?P<off>0x[0-9a-f]+))?$'
				op = None
				m = re.match(regex, arg)
				if m:
					base  = m.group('base')
					reg   = m.group('reg')
					scale = m.group('scale')
					arith = m.group('arith')
					off   = m.group('off')

					if reg:
						(r, _, mask) = regset.index_reg(reg)
						if not r:
							return None
						op = OpReg(r, mask)
						if scale:
							scale = int(scale)
							op = OpArith(op, Op(scale), OpArith.MUL)
					if base:
						(r, _, mask) = regset.index_reg(base)
						if not r:
							return None
						if op:
							op = OpArith(OpReg(r, mask), op, OpArith.ADD)
						else:
							op = OpReg(r, mask)
					if off:
						off = hex2int(off)
						if m.group('arith') == '-':
							op = OpArith(op, Op(off), OpArith.SUB)
						else:
							op = OpArith(op, Op(off), OpArith.ADD)

				return op

			if insn:
				insn = insn.strip()
			if arg1:
				arg1 = arg1.strip()
				if ishex(arg1):
					arg1 = hex2int(arg1)
				else:
					(addr_op, load_size) = match_addr(arg1)
					if addr_op:
						rip = match_rip(addr_op, address, size)
						if rip:
							if load_size:
								arg1 = OpLoad(Op(rip), load_size)
							else:
								arg1 = rip
						else:
							op = match_fmt(addr_op, self.regset)
							if op:
								if load_size:
									op = OpLoad(op, load_size)
								arg1 = op
			if arg2:
				arg2 = arg2.strip()
				if ishex(arg2):
					arg2 = hex2int(arg2)
				else:
					(addr_op, load_size) = match_addr(arg2)
					if addr_op:
						rip = match_rip(addr_op, address, size)
						if rip:
							if load_size:
								arg2 = OpLoad(Op(rip), load_size)
							else:
								arg2 = rip
						else:
							op = match_fmt(addr_op, self.regset)
							if op:
								if load_size:
									op = OpLoad(op, load_size)
								arg2 = op
			if comm:
				comm = comm.strip()
				if ishex(comm):
					comm = hex2int(comm)

			if insn_type == opcodes.InstructionType.BRANCH:
				if insn != 'ret' and target:
					bb = self.cur_func.add_bblock(target)
					self.cur_bb.targets.add(bb)

				self.cur_bb.end = address + size
				return opcodes.PYBFD_DISASM_STOP

			if self.cur_bb.end and address >= self.cur_bb.end:
				bb = self.cur_func.add_bblock(address)
				self.cur_bb.targets.add(bb)
				return opcodes.PYBFD_DISASM_STOP

			if insn_type == opcodes.InstructionType.COND_BRANCH:
				next_bb = self.cur_func.add_bblock(address + size)
				bb = self.cur_func.add_bblock(target)

				self.cur_bb.end = address + size
				self.cur_bb.targets.add(bb)
				self.cur_bb.targets.add(next_bb)
				self.cur_bb = next_bb

				if next_bb in self.cur_func.new_bblocks:
					self.cur_func.new_bblocks.remove(next_bb)
					self.cur_func.bblocks.append(next_bb)

			elif insn_type == opcodes.InstructionType.JSR:
				if target:
					self.add_entry(target)
					self.cur_bb.insts.append(InstCall(self.cur_bb, address, disassembly, [target]))

			elif insn_type == opcodes.InstructionType.COND_JSR:
				if target:
					self.add_entry(target)
					self.cur_bb.insts.append(InstCall(self.cur_bb, address, disassembly, [target]))

			elif insn_type == opcodes.InstructionType.NON_BRANCH:
				if insn == 'syscall' or insn == 'sysenter':
					self.cur_bb.insts.append(InstSyscall(self.cur_bb, address, disassembly))

				elif insn == 'lea':
					if isinstance(arg2, (int, long)):
						if arg2 >= self.start and arg2 < self.end:
							self.add_entry(arg2)
							self.cur_bb.insts.append(InstCall(self.cur_bb, address, disassembly, [arg2]))

					else:
						print "%x: %s" % (address, arg2)

				else:
					self.cur_bb.insts.append(Inst(self.cur_bb, address, disassembly))

			return opcodes.PYBFD_DISASM_CONTINUE

		def start_process(self, content):
			self.initialize_smart_disassemble(content, self.start)

			while len(self.entries):
				addr = self.entries[0]

				self.cur_func = Func(addr)
				self.cur_func.add_bblock(addr)
				self.entries.remove(addr)
				print "%x:" % (addr)

				while self.cur_func.new_bblocks:
					bb = self.cur_func.new_bblocks[0]
					self.cur_bb = bb
					self.cur_func.new_bblocks.remove(bb)
					self.cur_func.bblocks.append(bb)

					self.start_smart_disassemble(bb.start - self.start, self.process_instructions)

				def bb_cmp(x, y):
					return cmp(x.start, y.start)

				self.cur_func.bblocks = sorted(self.cur_func.bblocks, bb_cmp)
				self.funcs.append(self.cur_func)
				self.nfuncs += 1
				self.nbblocks += len(self.cur_func.bblocks)

	codes = CodeOpcodes(bfd, text_area[0], text_area[1])

	for sym_addr in dynsyms.keys():
		if sym_addr:
			codes.add_entry(sym_addr)

	if entry_addr:
		codes.add_entry(entry_addr)

	if init_addr:
		codes.add_entry(init_addr)

	if fini_addr:
		codes.add_entry(fini_addr)

	if init_area:
		init_content = bfd.sections.get('.init_array').content
		off = 0
		while off < len(init_content):
			addr = struct.unpack(ptr_fmt, init_content[off:off + ptr_size])[0]
			codes.add_entry(addr)
			off += ptr_size

	if fini_area:
		fini_content = bfd.sections.get('.fini_array').content
		off = 0
		while off < len(fini_content):
			addr = struct.unpack(ptr_fmt, init_content[off:off + ptr_size])[0]
			codes.add_entry(addr)
			off += ptr_size

	text_content = bfd.sections.get('.text').content
	codes.start_process(text_content)

	print "Dynamic Symbols: %d" % (len(dynsyms))
	print "Functions: %d" % (codes.nfuncs)
	print "Basic Blocks: %d" % (codes.nbblocks)

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
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('call_addr', 'INT', ''),
			('call_name', 'VARCHAR', '')],
			[],
			[['pkg_id', 'bin_id']])

binary_unknown_call_table = Table('binary_unknown_call', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('known', 'BOOLEAN', ''),
			('call_addr', 'INT', ''),
			('call_name', 'VARCHAR', '')],
			['pkg_id', 'bin_id', 'func_addr', 'target', 'known'],
			[['pkg_id', 'bin_id', 'known']])

binary_syscall_table = Table('binary_syscall', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('syscall', 'SMALLINT', 'NOT NULL')],
			[],
			[['pkg_id', 'bin_id']])

binary_unknown_syscall_table = Table('binary_unknown_syscall', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('known', 'BOOLEAN', ''),
			('syscall', 'SMALLINT', '')],
			['pkg_id', 'bin_id', 'func_addr', 'target', 'known'],
			[['pkg_id', 'bin_id', 'known']])

binary_vecsyscall_table = Table('binary_vecsyscall', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('syscall', 'SMALLINT', 'NOT NULL'),
			('request', 'BIGINT', 'NOT NULL')],
			[],
			[['pkg_id', 'bin_id']])

binary_unknown_vecsyscall_table = Table('binary_unknown_vecsyscall', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('syscall', 'SMALLINT', 'NOT NULL'),
			('target', 'VARCHAR', 'NOT NULL'),
			('known', 'BOOLEAN', ''),
			('request', 'BIGINT', '')],
			['pkg_id', 'bin_id', 'func_addr', 'syscall', 'target', 'known'],
			[['pkg_id', 'bin_id', 'known']])

binary_fileaccess_table = Table('binary_fileaccess', [
			('pkg_id', 'INT', 'NOT NULL'),
			('bin_id', 'INT', 'NOT NULL'),
			('func_addr', 'INT', 'NOT NULL'),
			('file', 'VARCHAR', 'NOT NULL')],
			[],
			[['pkg_id', 'bin_id']])

def BinaryCallgraph_run(jmgr, sql, args):
	sql.connect_table(binary_call_table)
	sql.connect_table(binary_unknown_call_table)
	sql.connect_table(binary_syscall_table)
	sql.connect_table(binary_unknown_syscall_table)
	sql.connect_table(binary_vecsyscall_table)
	sql.connect_table(binary_unknown_vecsyscall_table)
	sql.connect_table(binary_fileaccess_table)

	pkgname = args[0]
	bin = args[1]
	dir = args[2]
	pkg_id = args[3]
	bin_id = args[4]
	ref = args[5]

	exc = None
	try:
		path = dir + '/' + bin
		if not os.path.exists(path):
			raise Exception('path ' + path + ' does not exist')

		callers = get_callgraph(path)
		pkg_id = get_pkgname_id(sql, pkgname)
		bin_id = get_path_id(sql, bin)
		calls = []
		unknown_calls = []
		syscalls = []
		unknown_syscalls = []
		vecsyscalls = []
		unknown_vecsyscalls = []
		fileaccess = []

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
					values['syscall'] = syscall
					syscalls.append(values)
					continue

				if isinstance(syscall, str):
					values['target'] = syscall[1:-1]
				else:
					values['target'] = ''
				unknown_syscalls.append(values)

			for syscall in caller.vecsyscalls:
				for request in caller.vecsyscalls[syscall]:
					values = dict()
					values['func_addr'] = caller.func_addr
					values['syscall'] = syscall

					if isinstance(request, int) or isinstance(request, long):
						values['request'] = request
						vecsyscalls.append(values)
						continue

					if isinstance(request, str):
						values['target'] = request[1:-1]
					else:
						values['target'] = ''
					unknown_vecsyscalls.append(values)

			for file in caller.files:
				values = dict()
				values['func_addr'] = caller.func_addr
				values['file'] = file
				fileaccess.append(values)

		if not fileaccess:
			for file in get_fileaccess(path):
				values = dict()
				values['func_addr'] = 0
				values['file'] = file
				fileaccess.append(values)

		condition = 'pkg_id=\'' + Table.stringify(pkg_id) + '\' and bin_id=\'' + Table.stringify(bin_id) + '\''
		condition_unknown = condition + ' and known=False'
		sql.delete_record(binary_call_table, condition)
		sql.delete_record(binary_unknown_call_table, condition_unknown)
		sql.delete_record(binary_syscall_table, condition)
		sql.delete_record(binary_unknown_syscall_table, condition_unknown)
		sql.delete_record(binary_vecsyscall_table, condition)
		sql.delete_record(binary_unknown_vecsyscall_table, condition_unknown)
		sql.delete_record(binary_fileaccess_table, condition)

		for values in calls:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			sql.append_record(binary_call_table, values)

		for values in unknown_calls:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['known'] = False
			sql.append_record(binary_unknown_call_table, values)

		for values in syscalls:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			sql.append_record(binary_syscall_table, values)

		for values in unknown_syscalls:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['known'] = False
			sql.append_record(binary_unknown_syscall_table, values)

		for values in vecsyscalls:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			sql.append_record(binary_vecsyscall_table, values)

		for values in unknown_vecsyscalls:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['known'] = False
			sql.append_record(binary_unknown_vecsyscall_table, values)

		for values in fileaccess:
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			sql.append_record(binary_fileaccess_table, values)

		sql.update_record(package.binary_list_table, {'callgraph': False}, condition)
		sql.commit()

	except Exception as err:
		exc = sys.exc_info()

	if package.dereference_dir(dir, ref):
		package.remove_dir(dir)

def BinaryCallgraph_job_name(args):
	return "Binary Callgraph: " + args[1] + " in " + args[0]

BinaryCallgraph = Task(
	name="Binary Callgraph",
	func=BinaryCallgraph_run,
	arg_defs=[],
	job_name=BinaryCallgraph_job_name)

def BinaryCallInfo_run(jmgr, sql, args):
	pkgname = args[0]
	if len(args) == 1:
		pkgname_id = get_pkgname_id(sql, pkgname)
	else:
		pkgname_id = int(args[1])

	packages = package.search_latest_packages(sql, pkgname_id, pkgname)

	if not packages:
		return

	for (pkg_id, pkg) in packages:
		binaries = package.search_binary_list(sql, pkg_id, ['EXE', 'LIB'])
		if not binaries:
			continue

		target = package.get_package(pkg.source)
		dir = package.unpack_package(target)
		if not dir:
			continue

		for bin_id in binaries:
			bin = get_path(sql, bin_id)
			ref = package.reference_dir(dir)
			BinaryCallgraph.create_job(jmgr, [pkgname, bin, dir, pkg_id, bin_id, ref])

def BinaryCallInfo_job_name(args):
	return "Binary Call Info: " + args[0]

BinaryCallInfo = Task(
	name="Binary Call Info",
	func=BinaryCallInfo_run,
	arg_defs=["Package Name"],
	job_name=BinaryCallInfo_job_name)

def BinaryCallInfoByNames_run(jmgr, sql, args):
	for name in args[0].split():
		BinaryCallInfo.create_job(jmgr, [name])

def BinaryCallInfoByNames_job_name(args):
	return "Binary Call Info By Names: " + args[0]

BinaryCallInfoByNames = Task(
	name="Binary Call Info By Names",
	func=BinaryCallInfoByNames_run,
	arg_defs=["Package Names"],
	job_name=BinaryCallInfoByNames_job_name)

def BinaryCallInfoByPrefixes_run(jmgr, sql, args):
	for prefix in args[0].split():
		for (pkgname_id, pkgname) in get_pkgnames_by_prefix(sql, prefix):
			BinaryCallInfo.create_job(jmgr, [pkgname, pkgname_id])

def BinaryCallInfoByPrefixes_job_name(args):
	return "Binary Call Info By Prefixes: " + args[0]

BinaryCallInfoByPrefixes = Task(
	name="Binary Call Info By Prefixes",
	func=BinaryCallInfoByPrefixes_run,
	arg_defs=["Package Prefixes"],
	job_name=BinaryCallInfoByPrefixes_job_name)

def BinaryCallInfoByRanks_run(jmgr, sql, args):
	for pkgname in get_packages_by_ranks(sql, int(args[0]), int(args[1])):
		BinaryCallInfo.create_job(jmgr, [pkgname])

def BinaryCallInfoByRanks_job_name(args):
	return "Binary Call Info By Ranks: " + args[0] + " to " + args[1]

BinaryCallInfoByRanks = Task(
	name="Binary Call Info By Ranks",
	func=BinaryCallInfoByRanks_run,
	arg_defs=["Minimum Rank", "Maximum Rank"],
	job_name=BinaryCallInfoByRanks_job_name)

if __name__ == "__main__":
	get_callgraph(sys.argv[1])
