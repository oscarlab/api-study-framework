#!/usr/bin/python

from sql import tables, Table
from id import get_binary_id, get_package_id
import package
import os_target
import main
from utils import null_dev

import os
import sys
import re
import subprocess
import struct
import string
from sets import Set
import traceback
import logging

sys.path.append('pybfd/lib/python')
from pybfd import opcodes, bfd, section
from pybfd.opcodes import Opcodes, OpcodesException
from pybfd.bfd import Bfd, BfdException
from pybfd.symbol import SymbolFlags

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

def is_hex(s):
	try:
		int(s, 16)
		return True
	except ValueError:
		return False

def hex2int(str):
	return int(str[2:], 16)

class Register:
	def __init__(self, names):
		self.names = names
		self.masks = []
		self.sizes = []
		self.concrete = False
		self.value = 0
		mask = 256
		size = 1
		for n in names[::-1]:
			self.masks.insert(0, (mask - 1))
			self.sizes.insert(0, size)
			mask = mask * mask
			size = size + size

	def __str__(self):
		return self.names[0]

	def index_reg(self, regname):
		i = 0
		while i < len(self.names):
			if regname == self.names[i]:
				return (self.sizes[i], self.masks[i])
			i += 1
		return (None, None)

	def get_val(self, regname):
		i = 0
		while i < len(self.names):
			if regname == self.names[i]:
				if self.concrete == True:
					#logging.info('match and concrete')
					return self.value & self.masks[i]
			i += 1
		return None

	def set_val(self, regname, value):
		i = 0
		while i < len(self.names):
			if regname == self.names[i]:
				# if self.concrete == True:
				if value is None:
					logging.info(regname)
					logging.info('being set to None')
				self.value = value
				return
			i += 1

	def set_concreteness(self, regname, concreteness):
		i = 0
		while i < len(self.names):
			if str(regname) == self.names[i]:
				if concreteness != True and concreteness != False:
					return
				self.concrete = concreteness
				return
			i += 1

	def isconcrete(self, regname):
		i = 0
		while i < len(self.names):
			if str(regname) == self.names[i]:
				return self.concrete
			i += 1

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
		return (None, None, None)

	def get_val(self, regname):
		for reg in self.regs:
			val = reg.get_val(str(regname))
			if val is not None:
				return val
		return None

	def set_val(self,regname, value):
		for reg in self.regs:
			reg.set_val(regname, value)

	def set_concreteness(self, regname, concreteness):
		for reg in self.regs:
			reg.set_concreteness(regname, concreteness)

	def isconcrete(self, regname):
		for reg in self.regs:
			return reg.isconcrete(regname)

def get_x86_opcodes(binbytes):
	PREFIX = range(0x40, 0x50) + [0xf3, 0xf2, 0xf0, 0x2e, 0x36, 0x3e, 0x26] + range(0x64, 0x68)
	PREFIX = [chr(c) for c in PREFIX]
	TWOBYTE = [chr(0x0f)]
	THREEBYTE = [chr(0x38), chr(0x3a), chr(0x7a)]
	prefixes = ''
	i = 0
	while i < len(binbytes) and binbytes[i] in PREFIX:
		prefixes += binbytes[i]
		i += 1

	opcode = ''
	if len(binbytes) > i:
		opcode = binbytes[i]
	if len(binbytes) > i + 1 and binbytes[i] in TWOBYTE:
		opcode += binbytes[i + 1]
	if len(binbytes) > i + 2 and binbytes[i] in TWOBYTE and binbytes[i + 1] in THREEBYTE:
		opcode += binbytes[i + 2]
#	if opcode and prefixes:
	return opcode, prefixes

class Instr:
	def __init__(self, addr, dism, size, binbytes):
		self.addr = addr
		self.dism = dism
		self.size = size
		self.binbytes = binbytes
		self.opcode, self.prefixes = get_x86_opcodes(binbytes)

	def __str__(self):
		return "%x:        (%s)" % (self.addr, self.dism)

	def get_binbytes(self):
		return self.binbytes

	def get_instr(self):
		splitdism = self.dism.split()
		if splitdism[0] == 'repz' or splitdism[0] == "rep" or splitdism[0] == "repnz":
			return (splitdism[0]+" "+splitdism[1])
		if splitdism[0] == "lock":
			return splitdism[1]
		rege = r'rex\.[rwxbRWXB]*'
		if re.match(rege, splitdism[0]):
			if len(splitdism) > 1:
				return splitdism[1]
			else:
				return None
		return splitdism[0]

class InstrJCond(Instr):
	def __init__(self, addr, dism, target, size, binbytes):
		Instr.__init__(self, addr, dism, size, binbytes)
		self.target = target
		self.size = size

	def __str__(self):
		if isinstance(self.target, (int, long)):
			return "%x: %s %x" % (self.addr, self.dism, self.target)
		else:
			return "%x: %s %s" % (self.addr, self.dism, str(self.target))

class InstrMov(Instr):
	def __init__(self, addr, dism, reg, source, size, binbytes):
		Instr.__init__(self, addr, dism, size, binbytes)
		self.reg = reg
		self.source = source

	def __str__(self):
		return "%x: %s=%s" % (self.addr, str(self.reg), str(self.source))

class InstrCall(Instr):
	def __init__(self, addr, dism, target, size, binbytes):
		Instr.__init__(self, addr, dism, size, binbytes)
		self.target = target

	def __str__(self):
		if isinstance(self.target, (int, long)):
			return "%x: call %x" % (self.addr, self.target)
		else:
			return "%x: call %s" % (self.addr, str(self.target))

class Func:
	def __init__(self, start, end=None):
		if isinstance(start, long):
			start = start & 0xffffffffffffffff
		self.start = start
		self.end = end
		self.instrs = []
		self.targets = Set()
		self.num_calls = 0
		self.num_missed_calls = 0

class Op:
	def __init__(self, val=None):
		if isinstance(val, long):
			val = val & 0xffffffffffffffff
		self.val = val

	def __str__(self):
		return str(self.val)

	def get_val(self, regset=None):
		return self.val

class OpBogus(Op):
	def __init__(self, originalval):
		self.strval = originalval

	def __str__(self):
		return self.strval

	def get_val(self, regset=None):
		return None

class OpReg(Op):
	def __init__(self, reg, mask):
		Op.__init__(self)
		self.reg = reg
		self.mask = mask

	def __str__(self):
		return "<" + str(self.reg) + ">"

	def get_val(self, regset=None):
		if regset:
			return regset.get_val(self.reg)

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

	def __str__(self):
		if self.arith == self.ADD:
			return "(" + str(self.op1) + "+" + str(self.op2) + ")"
		if self.arith == self.SUB:
			return "(" + str(self.op1) + "-" + str(self.op2) + ")"
		if self.arith == self.MUL:
			return "(" + str(self.op1) + "*" + str(self.op2) + ")"
		if self.arith == self.DIV:
			return "(" + str(self.op1) + "/" + str(self.op2) + ")"
		return "unknown"

	def get_val(self, regset=None):
		val1 = self.op1.get_val(regset)
		val2 = self.op2.get_val(regset)
		if val1 is not None and val2 is not None:
			if self.arith == self.ADD:
				return val1 + val2
			if self.arith == self.SUB:
				return val1 - val2
			if self.arith == self.MUL:
				return val1 * val2
			if self.arith == self.DIV:
				return val1 / val2
		#logging.info('val1 and/or 2 is/are None')
		return None

class OpLoad(Op):
	def __init__(self, addr, size):
		Op.__init__(self)
		self.addr = addr
		self.size = size

	def get_val(self, regset=None):
		return None

	def get_addr(self, regset=None):
		return self.addr.get_val(regset)

class Memory:
	def __init__(self):
		self.memory = {}
		self.stack = {}

	def set_val(self, address, val):
		self.memory[address] = val

	def get_val(self, address):
		if address in self.memory.keys():
			return self.memory[address]

	def push(self, key, val):
		if val is not None:
			self.stack[key] = val

	def pop(self, key):
		if key in self.stack.keys():
			return self.stack.pop(key)
		else:
			return None


def val2ptr(val, ptr_size):
	if ptr_size == 8:
		max = 0xffffffffffffffff
	elif ptr_size == 4:
		max = 0xffffffff
	else:
		return 0

	if isinstance(val, long):
		return val & max

	if val < 0:
		return max + val - 1

	return val

def get_callgraph(binary_name, print_screen=False, analysis=False, emit_corpus=False, sql=None, pkg_id=None, bin_id=None, fileToPrintTo=None):

	# Initialize BFD instance
	bfd = Bfd(binary_name)

	if bfd.target == 'elf64-x86-64':
		ptr_fmt = '<Q'
		ptr_size = 8
		elf_word_fmt = '<L'
		elf_word_size = 4
	elif bfd.target == 'elf32-i386':
		ptr_fmt = '<L'
		ptr_size = 4
		elf_word_fmt = '<H'
		elf_word_size = 2
	else:
		raise Exception("unknown target: " + bfd.target)

	entry_addr = bfd.start_address
	dynsyms = bfd.symbols

	symbol_names = []
	if '.dynsym' in bfd.sections and '.dynstr' in bfd.sections:
		symtab = bfd.sections['.dynsym'].content
		strtab = bfd.sections['.dynstr'].content
		off = 0
		while off + ptr_size <= len(symtab):
			st_name_off = struct.unpack(elf_word_fmt, symtab[off:off + elf_word_size])[0]
			st_name = ""
			while st_name_off < len(strtab) and strtab[st_name_off] != '\0':
				st_name += strtab[st_name_off]
				st_name_off += 1
			symbol_names.append(st_name)
			if ptr_size == 8:
				off += 24
			else:
				off += 12

	rel_entries = dict()
	if '.rela.plt' in bfd.sections or '.rel.plt' in bfd.sections:
		key = '.rela.plt'
		if key not in bfd.sections:
			key = 'rel.plt'
		sec = bfd.sections[key]

		content = sec.content
		off = 0
		while off + ptr_size * 2 <= len(content):
			r_offset = struct.unpack(ptr_fmt, content[off:off + ptr_size])[0]
			off += ptr_size
			r_info = struct.unpack(ptr_fmt, content[off:off + ptr_size])[0]
			off += ptr_size
			if key == '.rela.plt':
				r_addend = struct.unpack(ptr_fmt, content[off:off + ptr_size])[0]
				off += ptr_size
			else:
				r_addend = 0
			if ptr_size == 8:
				r_sym = r_info >> 32
			else:
				r_sym = r_info >> 8

			if r_sym:
				rel_entries[r_offset] = symbol_names[r_sym]

	class CodeOpcodes(Opcodes):
		def __init__(self, bfd):
			Opcodes.__init__(self, bfd)

			if bfd.target == 'elf64-x86-64':
				self.regset = RegisterSet(x86_64_regs)
			elif bfd.target == 'elf32-i386':
				self.regset = RegisterSet(i386_regs)

			self.start = self.end = None
			for name, sec in bfd.sections.items():
				if self.start == None or self.start > sec.vma:
					self.start = sec.vma
				if self.end == None or self.end < sec.vma + sec.size:
					self.end = sec.vma + sec.size

			self.entries = []
			self.processed_entries = []
			self.num_instrs = 0
			self.funcs = []
			self.cur_func = None
			self.nfuncs = 0
			self.mem = Memory()
			# self.nbblocks = 0
			# self.regval = {}
			# self.regconcreteness = {}

		def set_range(self,start, end, executable):
			self.start = start
			self.end = end
			if executable is True:
				self.add_entry(start)

		def set_nonconcrete(self):
			for reg in ['rax','rcx','rdx','rsi','rdi','r8','r9','r10','r11']:
				self.regset.set_concreteness(reg,False)

		def add_entry(self, addr):
			if self.cur_func and self.cur_func.start == addr:
				return

			if addr in self.entries:
				return

			if addr in self.processed_entries:
				return

			for func in self.funcs:
				if addr == func.start:
					return

			self.entries.append(addr)

		def process_instructions(self, address, size, branch_delay_insn,
			insn_type, target, target2, disassembly):
			binbytes = self.content[address - self.start:address - self.start + size]
			#logging.info(insn_type)
			#logging.info(address)
			#logging.info(disassembly)

			try:
				regex = r'^(?P<rex>rex\.[wrWR]+ )?(?P<repz>repz )?(?P<insn>\S+)(\s+(?P<arg1>[^,]+)?(,(?P<arg2>[^#]+)(#(?P<comm>.+))?)?)?$'
				m = re.match(regex, disassembly)

				if not m:
					return opcodes.PYBFD_DISASM_CONTINUE
				rex = m.group('rex')
				repz = (m.group('repz') is not None)
				insn = m.group('insn')
				arg1 = m.group('arg1')
				arg2 = m.group('arg2')
				comm = m.group('comm')

				def match_addr(arg):
					regex = r'^(?P<load>(?P<size>QWORD|DWORD|WORD|BYTE) PTR )?\[(?P<addr>[^\]]+)\]'
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

				def match_pc(arg, addr, size):
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

						if base:
							(r, _, mask) = regset.index_reg(base)
							if not r:
								return None
							op = OpReg(r, mask)
						if reg:
							(r, _, mask) = regset.index_reg(reg)
							if not r:
								return None
							if op is not None:
								op2 = OpReg(r, mask)
								if scale:
									scale = int(scale)
									op2 = OpArith(op2, Op(scale), OpArith.MUL)
								op = OpArith(op, op2, OpArith.ADD)
							else: #Op is still None? How
								op = OpReg(r,mask)
								if scale:
									scale = int(scale)
									op = OpArith(op, Op(scale), OpArith.MUL)
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
						arg1 = Op(hex2int(arg1))
					else:
						(addr_op, load_size) = match_addr(arg1)
						if addr_op:
							pc = match_pc(addr_op, address, size)
							if pc:
								arg1 = Op(pc)
								if load_size:
									arg1 = OpLoad(arg1, load_size)
							else:
								op = match_fmt(addr_op, self.regset)
								if op:
									if load_size:
										op = OpLoad(op, load_size)
									arg1 = op
						elif self.regset.is_reg(arg1):
							(r, _, mask) = self.regset.index_reg(arg1)
							if r != None and mask !=None:
								arg1 = OpReg(r, mask)
						else:
							arg1 = OpBogus(arg1)

				if arg2:
					arg2 = arg2.strip()
					if ishex(arg2):
						arg2 = Op(hex2int(arg2))
					else:
						(addr_op, load_size) = match_addr(arg2)
						if addr_op:
							pc = match_pc(addr_op, address, size)
							if pc:
								arg2 = Op(pc)
								if load_size:
									arg2 = OpLoad(arg2, load_size)
							else:
								op = match_fmt(addr_op, self.regset)
								if op:
									if load_size:
										op = OpLoad(op, load_size)
									arg2 = op
						elif self.regset.is_reg(arg2):
							(r, _, mask) = self.regset.index_reg(arg2)
							if r != None and mask != None:
								arg2 = OpReg(r, mask)
						else:
							arg2 = OpBogus(arg2)
				if comm:
					comm = comm.strip()
					if ishex(comm):
						comm = hex2int(comm)

				if self.cur_func.end and address >= self.cur_func.end:
					return opcodes.PYBFD_DISASM_STOP

				self.num_instrs += 1

				if insn == 'data16':
					return opcodes.PYBFD_DISASM_CONTINUE

				#if insn_type == opcodes.InstructionType.BRANCH:
				# if insn_type == opcodes.InstructionType.COND_BRANCH:

				# rbp, rbx, r12, r13, r14, r15 are callee-preserved,
				# so they will always be concrete
				# On a call the rest must be set to non-concrete
				# Must implement push and pop
				# Popping a register makes it concrete
				if insn_type == opcodes.InstructionType.JSR or insn_type == opcodes.InstructionType.COND_JSR: #CALL
					target_addr = None
					if isinstance(arg1, OpLoad):
						target_addr = arg1.addr.get_val()
					elif isinstance(arg1, OpReg):
						target_addr = arg1.get_val(self.regset)
					if target_addr:
						if target_addr > 0xff and target_addr < 0x80000000:
							if target_addr in rel_entries:
								self.cur_func.instrs.append(InstrCall(address,
											disassembly,
											rel_entries[target_addr],
											size, binbytes))
							else:
								#val2p = val2ptr(target_addr, ptr_size)
								#if val2p < self.start or val2p >= self.end:
								#	print "Adding to entries:", hex(val2p), hex(self.start), hex(self.end)
								#	self.add_entry(val2ptr(target_addr, ptr_size))
								self.cur_func.instrs.append(InstrCall(address,
											disassembly,
											target_addr, size, binbytes))
						else:
							logging.info("Target_addr out of valid bounds")
							logging.info(disassembly)
							logging.info(insn)
							logging.info(arg1)
							logging.info(arg2)
							logging.info(target_addr)
							logging.info(" ")
					elif target:
#						val2p = val2ptr(target,ptr_size)
#						if val2p < self.start or val2p >= self.end:
#							print "Adding to entries:", hex(val2p), hex(self.start), hex(self.end)
#							self.add_entry(val2p)
						self.cur_func.instrs.append(InstrCall(address,
											disassembly,
											target, size, binbytes))
					else:
						if insn == 'call':
							self.cur_func.num_missed_calls += 1
					# Not redundant. Looks kinda odd, but
					# setting registers to non-concrete
					# has to be at the end
					if insn == 'call':
						self.cur_func.num_calls += 1
						self.set_nonconcrete()

				elif insn_type == opcodes.InstructionType.NON_BRANCH:
					if insn == 'mov':
						if isinstance(arg1, OpReg):
							val = None
							self.cur_func.instrs.append(InstrMov(address,
											disassembly,
											arg1.reg, arg2,
											size, binbytes))
							if isinstance(arg2,Op) and not isinstance(arg2,OpLoad):
								val = arg2.get_val(self.regset)
							elif isinstance(arg2,OpLoad):
								addr = arg2.get_addr(self.regset)
								if addr is not None:
									val = self.mem.get_val(addr)
							if val is not None:
								self.regset.set_concreteness(str(arg1.reg), True)
								self.regset.set_val(str(arg1.reg), val)
						else:
							if isinstance(arg1, OpLoad):
								addr = arg1.get_addr(self.regset)
								val = arg2.get_val(self.regset)
								if addr is not None and val is not None:
									self.mem.set_val(addr, val)
							self.cur_func.instrs.append(Instr(address,
											disassembly,
											size, binbytes))

					elif insn == 'lea':
						if isinstance(arg1, OpReg):
							val = None
							self.cur_func.instrs.append(InstrMov(address,
											disassembly,
											arg1.reg, arg2,
											size, binbytes))
							if isinstance(arg2,Op) and not isinstance(arg2, OpLoad):
								val = arg2.get_val(self.regset)
							elif isinstance(arg2,OpLoad):
								addr = arg2.get_addr(self.regset)
								if addr is not None:
									val = self.mem.get_val(addr)
							if val is not None:
								self.regset.set_concreteness(str(arg1.reg), True)
								self.regset.set_val(str(arg1.reg), val)
						else:
							self.cur_func.instrs.append(Instr(address,
										disassembly,
										size, binbytes))

					elif insn == 'push':
						if isinstance(arg1, OpReg):
							if self.regset.isconcrete(str(arg1.reg)):
								self.mem.push(arg1.reg, arg1.get_val(self.regset))
						self.cur_func.instrs.append(Instr(address, disassembly, size, binbytes))

					elif insn == 'pop':
						if isinstance(arg1, OpReg):
							val = self.mem.pop(arg1.reg)
							if val is not None:
								self.regset.set_concreteness(arg1.reg, True)
								self.regset.set_val(arg1.reg, val)
						self.cur_func.instrs.append(Instr(address, disassembly, size, binbytes))

					else:
						self.cur_func.instrs.append(Instr(address, disassembly, size, binbytes))
				else:
					self.cur_func.instrs.append(Instr(address, disassembly, size, binbytes))

			except Exception as e:
				traceback.print_exc()
				return opcodes.PYBFD_DISASM_STOP

			return opcodes.PYBFD_DISASM_CONTINUE

		def print_to_screen(self, func):
			print "-------------"
			print "func %x:" % (func.start)

			opcodes = dict()
			calls = []

			if func.num_calls != 0:
				print "Function_address:", func.start,
				miss_rate = func.num_missed_calls / (func.num_calls * 1.0)
				print "miss_rate", miss_rate * 100

			for instr in func.instrs:
				if isinstance(instr, InstrCall):
					if isinstance(instr.target, int) or isinstance(instr.target, long):
						if not instr.target in calls:
							calls.append(instr.target)
					elif isinstance(instr.target, Op) and instr.target.val:
						if not instr.target.val in calls:
							calls.append(instr.target.val)

				opcode = instr.opcode
				size = instr.size
				prefix = instr.prefixes
				mnem = instr.get_instr()

				if mnem is None:
					continue

				if opcode == '':
					continue
				if prefix == '':
					prefix = chr(0x0)
				if (prefix, opcode, size, mnem) in opcodes:
					opcodes[(prefix, opcode, size, mnem)] += 1
				else:
					opcodes[(prefix, opcode, size, mnem)] = 1

			for call in calls:
				if isinstance(call, int) or isinstance(call, long):
					print "    call: %x" % (call)
				else:
					call_addr = None
					for addr, sym in codes.dynsyms.items():
						if sym.name == call:
							call_addr = sym.value
							break
					if call_addr:
						print "    call: %s (%x)" % (call, call_addr)
					else:
						print "    call: %s" % (call)

			for (prefix, opcode, size, mnem, dism), count in opcodes.items():
				print prefix.encode('hex'), opcode.encode('hex'), size, mnem,  count

		def clean_dism(self, dism):
			def getRegSize(reg):
				if reg in ['zmm0','zmm1','zmm2','zmm3','zmm4','zmm5','zmm6','zmm7','zmm8','zmm9','zmm10','zmm11','zmm12','zmm13','zmm14','zmm15','zmm16','zmm17','zmm18','zmm19','zmm20','zmm21','zmm22','zmm23','zmm24','zmm25','zmm26','zmm27','zmm28','zmm29','zmm30','zmm31']:
					return 'v512'
				elif reg in ['ymm0','ymm1','ymm2','ymm3','ymm4','ymm5','ymm6','ymm7','ymm8','ymm9','ymm10','ymm11','ymm12','ymm13','ymm14','ymm15','ymm16','ymm17','ymm18','ymm19','ymm20','ymm21','ymm22','ymm23','ymm24','ymm25','ymm26','ymm27','ymm28','ymm29','ymm30','ymm31']:
					return 'v256'
				elif reg in ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8','xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15','xmm16','xmm17','xmm18','xmm19','xmm20','xmm21','xmm22','xmm23','xmm24','xmm25','xmm26','xmm27','xmm28','xmm29','xmm30','xmm31']:
					return 'v128'
				elif reg in ['rax','rbx','rcx','rdx','rsi','rdi','rbp','rsp','r8','r9','r10','r11','r12','r13','r14','r15']:
					return 'r64'
				elif reg in ['eax','ebx','ecx','edx','esi','edi','ebp','esp','r8d','r9d','r10d','r11d','r12d','r13d','r14d','r15d']:
					return 'r32'
				elif reg in ['ax','bx','cx','dx','si','di','bp','sp','r8w','r9w','r10w','r11w','r12w','r13w','r14w','r15w']:
					return 'r16'
				elif reg in ['al','ah','bl','bh','cl','ch','dl','dh','sil','sih','dil','dih','bpl','bph','spl','sph','r8b','r9b','r10b','r11b','r12b','r13b','r14b','r15b']:
					return 'r8'
				else:
					return None
			m = re.search(r'(bad)',dism)
			if m:
				return None
			dism = re.sub("ZMMWORD PTR","",dism)
			dism = re.sub("YMMWORD PTR","",dism)
			dism = re.sub("XMMWORD PTR","",dism)
			dism = re.sub("QWORD PTR","",dism)
			dism = re.sub("DWORD PTR","",dism)
			dism = re.sub("WORD PTR","",dism)
			dism = re.sub("BYTE PTR","",dism)
			dism = re.sub("\s+","_", dism)
			dism = re.sub("#.*$","",dism)
			dism = re.sub("<.*$","",dism)
			dism = re.sub(",","_",dism)
			dism = re.sub("__","_",dism)
			m = re.search(r"0x[0-9a-f]+", dism)
			if m:
				value = int(m.group(0), 16)
				if value > 0x100 or value < -0x100:
					dism = re.sub("0x[a-f0-9]+","addr",dism)
				else:
					dism = re.sub("0x[a-f0-9]+","imm8",dism)
			dism = dism.rstrip("_")
			dism = re.sub('nop.*','nop',dism)
			dism = re.sub("rex(\.[WRXB]+)?\_","", dism)
			dism = re.sub('\[(r(s|b)p)\+(imm8|addr)?\]','stackVal',dism)
			dism = re.sub('\[([rabcdesiplh0-9wx]{3})[bwd]?((\+|\-|\*)(imm8|addr))?\]','memVal',dism)
			dism = re.sub('\[([rabcdesiplh0-9wx]{2}[rabcdesiplh0-9wx]?)[bwd]?((\+|\-|\*)(imm8|addr|(([rabcdesiplh0-9wx]{2}[rabcdesiplh0-9wx]?)[bwd]?)))?((\+|\-|\*)[0-9]+)?((\+|\-)(imm8|addr))?\]','memVal',dism)
			parts = dism.split('_')
			if parts[0] in ['push', 'pop']:
				regsize = getRegSize(parts[1])
				if regsize is not None:
					dism = re.sub(parts[1], regsize, dism)
			if len(parts) >= 4:
				regsize = getRegSize(parts[-3])
				if regsize is not None:
					dism = re.sub(parts[-3], regsize, dism)
			if len(parts) >= 3:
				regsize = getRegSize(parts[-2])
				if regsize is not None:
					dism = re.sub(parts[-2], regsize, dism)
			if len(parts) >= 2:
				regsize = getRegSize(parts[-1])
				if regsize is not None:
					dism = re.sub(parts[-1], regsize, dism)
			return dism

		def print_corpus(self, func):
			for instr in func.instrs:
				dism = self.clean_dism(instr.dism)
				if dism is not None:
					print dism + " ",
			print "\n"

		def print_corpus_to_file(self, func, fileToPrintTo):
			if fileToPrintTo is None:
				logging.info("file is none?")
				return
			for instr in func.instrs:
				dism = self.clean_dism(instr.dism)
				if dism is not None:
					fileToPrintTo.write(dism + " ")
			fileToPrintTo.write('\n')

		def insert_into_db(self, func, sql, pkg_id, bin_id):
			if sql == None or pkg_id == None or bin_id == None:
				logging.info("sql, pkg_id or bin_id was None??")
				traceback.print_exc()
				return

			opcodes = dict()
			calls = []
			if func.num_calls != 0:
				mrvalues = dict()
				mrvalues['pkg_id'] = pkg_id
				mrvalues['bin_id'] = bin_id
				mrvalues['func_addr'] = func.start
				miss_rate = func.num_missed_calls / (func.num_calls * 1.0)
				mrvalues['miss_rate'] = miss_rate * 100
				sql.append_record(tables['binary_call_missrate'], mrvalues)

			for instr in func.instrs:
				if isinstance(instr, InstrCall):
					if isinstance(instr.target, int) or isinstance(instr.target, long):
						if not instr.target in calls:
							calls.append(instr.target)
					elif isinstance(instr.target, Op) and instr.target.val:
						if not instr.target.val in calls:
							calls.append(instr.target.val)
				opcode = instr.opcode
				size = instr.size
				prefix = instr.prefixes
				mnem = instr.get_instr()
				if mnem is None:
					continue

				if opcode == '':
					continue
				if prefix == '':
					prefix = chr(0x0)
				if (prefix, opcode, size, mnem) in opcodes:
					opcodes[(prefix, opcode, size, mnem)] += 1
				else:
					opcodes[(prefix, opcode, size, mnem)] = 1

			for call in calls:
				values = dict()
				values['pkg_id'] = pkg_id
				values['bin_id'] = bin_id
				values['func_addr'] = func.start
				if isinstance(call, int) or isinstance(call, long):
					values['call_addr'] = call
				else:
					for addr, sym in codes.dynsyms.items():
						if sym.name == call:
							values['call_addr'] = sym.value
							break
					values['call_name'] = call
				sql.append_record(tables['binary_call'], values)

			for (prefix, opcode, size, mnem), count in opcodes.items():
				values = dict()
				values['pkg_id'] = pkg_id
				values['bin_id'] = bin_id
				values['func_addr'] = func.start
				values['prefix'] = int(prefix.encode('hex'), 16)
				values['opcode'] = int(opcode.encode('hex'), 16)
				values['size'] = size
				values['mnem'] = mnem
				values['count'] = count
				try:
					sql.append_record(tables['binary_opcode_usage'], values)
				except Exception as e:
					logging.info(e)
					logging.info(prefix.encode('hex'))
					logging.info(opcode)
					logging.info(int(opcode.encode('hex'),16))
					logging.info(size)
					logging.info(mnem)
					logging.info(count)
					continue

		def start_process(self, content, print_screen, analysis, emit_corpus, dynsym_list, sql,  pkg_id, bin_id, fileToPrintTo):
			self.content = content
			self.initialize_smart_disassemble(content, self.start)
			cont = True
			while cont:
				next = None
				for entry in self.entries:
					if entry >= self.start and entry < self.end:
						next = entry
						break

				if not next:
					break

				if next not in dynsym_list.keys():
					self.cur_func = Func(next)
				else:
					size = dynsym_list[next]
					size = int(size)
					if size == 0:
						self.cur_func = Func(next)
					else:
						self.cur_func = Func(next, next+size)
				self.entries.remove(next)
				self.processed_entries.append(next)

				self.start_smart_disassemble(self.cur_func.start - self.start, self.process_instructions)

				if emit_corpus is True:
					if print_screen is True:
						self.print_corpus(self.cur_func)
					else:
						self.print_corpus_to_file(self.cur_func, fileToPrintTo)

				if analysis is True:
					if print_screen is True:
						self.print_to_screen(self.cur_func)
					else:
						self.insert_into_db(self.cur_func, sql, pkg_id, bin_id)
				self.nfuncs += 1


	codes = CodeOpcodes(bfd)
	codes.dynsyms = dynsyms

	process = subprocess.Popen(["readelf", "--syms", "--dyn-syms","-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

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
		size = parts[2]
		if ishex(size):
			logging.info('Why is the size hex? Why is nothing standardized?')
			size = hex2int(size)
		dynsym_list[addr] = size

	if process.wait() != 0:
		raise Exception('process failed: readelf --dyn-syms')

	process = subprocess.Popen(["readelf", "--program-headers", "-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

	executable = None
	for line in process.stdout:
		parts = line.strip().split()
		if len(parts) < 6:
			continue
		if parts[0] == 'INTERP':
			executable = True

	if executable is None:
		executable = False

	if process.wait() != 0:
		raise Exception('process failed: readelf --program-headers')

	process = subprocess.Popen(["readelf", "--file-header", "-W", binary_name], stdout=subprocess.PIPE, stderr=null_dev)

	for line in process.stdout:
		parts = line.strip().split()
		if parts[1] == 'EXEC':
			executable = True

	if process.wait() != 0:
		raise Exception('process failed: readelf --program-headers')

	for sym_addr in dynsyms.keys():
		# Only look at global functions
		flags = dynsyms[sym_addr].flags
		if SymbolFlags.GLOBAL not in flags:
			continue
		if SymbolFlags.FUNCTION not in flags:
			continue
		if sym_addr:
			codes.add_entry(sym_addr)

#	if entry_addr:
#		codes.add_entry(entry_addr)

	if '.init' in bfd.sections:
		codes.add_entry(bfd.sections.get('.init').vma)

	if '.fini' in bfd.sections:
		codes.add_entry(bfd.sections.get('.fini').vma)

	if '.init_array' in bfd.sections:
		init_content = bfd.sections.get('.init_array').content
		off = 0
		while off + ptr_size <= len(init_content):
			addr = struct.unpack(ptr_fmt, init_content[off:off + ptr_size])[0]
			off += ptr_size

	if '.fini_array' in bfd.sections:
		fini_content = bfd.sections.get('.fini_array').content
		off = 0
		while off + ptr_size < len(fini_content):
			addr = struct.unpack(ptr_fmt, fini_content[off:off + ptr_size])[0]
			codes.add_entry(addr)
			off += ptr_size

	for key, sec in bfd.sections.items():
		if not (sec.flags & section.SectionFlags.CODE):
			continue

		content = sec.content
		codes.set_range(sec.vma, sec.vma + sec.size, executable)
		codes.start_process(content, print_screen, analysis, emit_corpus, dynsym_list, sql, pkg_id, bin_id, fileToPrintTo)


	if print_screen is True:
		print "-----------"
		print "Dynamic Symbols: %d" % (len(codes.dynsyms))
		print "Functions: %d" % (codes.nfuncs)

	# def Func_cmp(x, y):
	# 	return cmp(x.start, y.start)

	# codes.funcs = sorted(codes.funcs, Func_cmp)

	# return codes

def analysis_binary_instr_linear(sql, binary, pkg_id, bin_id):
	condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
	condition_unknown = condition + ' and known=False'
	sql.delete_record(tables['binary_call'], condition)
	sql.delete_record(tables['binary_call_unknown'], condition_unknown)
	sql.delete_record(tables['binary_opcode_usage'], condition)
	sql.delete_record(tables['binary_call_missrate'], condition)

	get_callgraph(binary, False, True, False, sql, pkg_id, bin_id)

def emit_corpus(binary, corpusFileName):
	with open(corpusFileName, 'w+') as fileToPrintTo:
		get_callgraph(binary, False, False, True, None, None, None, fileToPrintTo)
		fileToPrintTo.close()

if __name__ == "__main__":
	if len(sys.argv) == 3:
		if sys.argv[2] == 'emit-corpus':
			get_callgraph(sys.argv[1], True, False, True)
	else:
		get_callgraph(sys.argv[1], True, True, False)
