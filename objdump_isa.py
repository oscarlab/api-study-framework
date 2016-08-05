#!/usr/bin/python

from sql import tables, Table
from id import get_binary_id, get_package_id
import package
import os_target
import main

import os
import sys
import re
import subprocess
import struct
import string
from sets import Set
import traceback

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

	def __str__(self):
		return self.names[0]

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
		return (None, None, None)

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

	opcode = binbytes[0:i]
	if len(binbytes) > i:
		opcode += binbytes[i]
	if len(binbytes) > i + 1 and binbytes[i] in TWOBYTE:
		opcode += binbytes[i + 1]
	if len(binbytes) > i + 2 and binbytes[i] in TWOBYTE and binbytes[i + 1] in THREEBYTE:
		opcode += binbytes[i + 2]
	return opcode, prefixes

class Instr:
	def __init__(self, bb, addr, dism, size, binbytes):
		self.bblock = bb
		self.addr = addr
		self.dism = dism
		self.size = size
		self.opcode, self.prefixes = get_x86_opcodes(binbytes)

	def __str__(self):
		return "%x:        (%s)" % (self.addr, self.dism)

	def get_instr(self):
		splitdism = self.dism.split()
		if splitdism[0] == 'repz':
			return (splitdism[0]+" "+splitdism[1])
		return self.dism.split()[0]

class InstrJCond(Instr):
	def __init__(self, bb, addr, dism, target, size, binbytes):
		Instr.__init__(self, bb, addr, dism, size, binbytes)
		self.target = target
		self.size = size

	def __str__(self):
		if isinstance(self.target, (int, long)):
			return "%x: %s %x" % (self.addr, self.dism, self.target)
		else:
			return "%x: %s %s" % (self.addr, self.dism, str(self.target))

class InstrMov(Instr):
	def __init__(self, bb, addr, dism, reg, source, size, binbytes):
		Instr.__init__(self, bb, addr, dism, size, binbytes)
		self.reg = reg
		self.source = source

	def __str__(self):
		return "%x: %s=%s" % (self.addr, str(self.reg), str(self.source))

class InstrSave(Instr):
	def __init__(self, bb, addr, dism, target, reg, size, binbytes):
		Instr.__init__(self, bb, addr, dism ,size, binbytes)
		self.target = target
		self.reg = reg

	def __str__(self):
		return "%x: *%s=%s" % (self.addr, str(self.target), str(self.reg))

class InstrCall(Instr):
	def __init__(self, bb, addr, dism, target, size, binbytes):
		Instr.__init__(self, bb, addr, dism, size, binbytes)
		self.target = target

	def __str__(self):
		if isinstance(self.target, (int, long)):
			return "%x: call %x" % (self.addr, self.target)
		else:
			return "%x: call %s" % (self.addr, str(self.target))

class BBlock:
	def __init__(self, start, end=None):
		if isinstance(start, long):
			start = start & 0xffffffffffffffff
		if isinstance(end, long):
			end = end & 0xffffffffffffffff
		self.start = start
		self.end = end
		self.instrs = []
		self.targets = Set()

class Func:
	def __init__(self, entry):
		if isinstance(entry, long):
			entry = entry & 0xffffffffffffffff
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
					# print "passed through here %x, %x, %x" % (addr, bb.start, bb.end)
					new = BBlock(addr, bb.end)
					bb.end = addr

					splice = 0
					for instr in bb.instrs:
						if instr.addr >= addr:
							break
						splice += 1

					new.instrs = bb.instrs[splice:]
					bb.instrs = bb.instrs[:splice]
					if bb in self.new_bblocks:
						self.new_bblocks.append(new)
					else:
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
		if isinstance(val, long):
			val = val & 0xffffffffffffffff
		self.val = val

	def __str__(self):
		return str(self.val)

	def get_val(self, regval=None):
		return self.val

class OpReg(Op):
	def __init__(self, reg, mask):
		Op.__init__(self)
		self.reg = reg
		self.mask = mask

	def __str__(self):
		return "<" + str(self.reg) + ">"

	def get_val(self, regval=None):
		if regval and isinstance(regval[self.reg], (int, long)):
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

	def get_val(self, regval=None):
		val1 = self.op1.get_val(regval)
		val2 = self.op2.get_val(regval)
		if val1 and val2:
			if self.arith == self.ADD:
				return val1 + val2
			if self.arith == self.SUB:
				return val1 - val2
			if self.arith == self.MUL:
				return val1 * val2
			if self.arith == self.DIV:
				return val1 / val2
		return None

class OpLoad(Op):
	def __init__(self, addr, size):
		Op.__init__(self)
		self.addr = addr
		self.size = size

	def get_val(self, regval=None):
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

def get_callgraph(binary_name):

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
						#logging.info("Hello")
				self.regset = RegisterSet(i386_regs)

			self.start = self.end = None
			for name, sec in bfd.sections.items():
				if self.start == None or self.start > sec.vma:
					self.start = sec.vma
				if self.end == None or self.end < sec.vma + sec.size:
					self.end = sec.vma + sec.size

			self.entries = []
			self.funcs = []
			self.cur_func = None
			self.cur_bb = None
			self.nfuncs = 0
			self.nbblocks = 0

		def set_range(self,start, end):
			self.start = start
			self.end = end

		def add_entry(self, addr):
			# print "In add_entry: %x" % (addr)
			if self.cur_func and self.cur_func.entry == addr:
				return

			if addr in self.entries:
				return

			for func in self.funcs:
				if addr == func.entry:
					return

			self.entries.append(addr)

		def process_instructions(self, address, size, branch_delay_insn,
			insn_type, target, target2, disassembly):
			binbytes = self.content[address - self.start:address - self.start + size]
			#print "%x: %s" % (address, disassembly)

			try:
				regex = r'^(?P<repz>repz )?(?P<insn>\S+)(\s+(?P<arg1>[^,]+)?(,(?P<arg2>[^#]+)(#(?P<comm>.+))?)?)?$'
				m = re.match(regex, disassembly)

				if not m:
					return opcodes.PYBFD_DISASM_CONTINUE

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
							if op:
								op = OpArith(OpReg(r, mask), op, OpArith.ADD)
							else:
								op = OpReg(r, mask)
						if reg:
							(r, _, mask) = regset.index_reg(reg)
							if not r:
								return None
							op = OpReg(r, mask)
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
						else:
							(r, _, mask) = self.regset.index_reg(arg1)
							arg1 = OpReg(r, mask)

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
									arg2 = OpLoad(arg1, load_size)
							else:
								op = match_fmt(addr_op, self.regset)
								if op:
									if load_size:
										op = OpLoad(op, load_size)
									arg2 = op
						else:
							(r, _, mask) = self.regset.index_reg(arg2)
							arg2 = OpReg(r, mask)

				if comm:
					comm = comm.strip()
					if ishex(comm):
						comm = hex2int(comm)

				if insn == 'ret' or insn == 'hlt':
					self.cur_bb.end = address + size
					self.cur_bb.instrs.append(Instr(self.cur_bb, address, disassembly, size, binbytes))
					return opcodes.PYBFD_DISASM_STOP

				if insn_type == opcodes.InstructionType.BRANCH:
					if isinstance(arg1, OpLoad):
						target_addr = arg1.addr.get_val()
						if target_addr in rel_entries:
							self.cur_bb.instrs.append(InstrCall(self.cur_bb,
											address,
											disassembly,
											rel_entries[target_addr],
											size, binbytes))
						elif target_addr:
							self.add_entry(val2ptr(target_addr, ptr_size))
							self.cur_bb.instrs.append(InstrCall(self.cur_bb,
											address,
											disassembly,
											target_addr, size, binbytes))

					if target:
						bb = self.cur_func.add_bblock(val2ptr(target, ptr_size))
						self.cur_bb.targets.add(bb)

					self.cur_bb.end = address + size
					return opcodes.PYBFD_DISASM_STOP

				if self.cur_bb.end and address >= self.cur_bb.end:
					bb = self.cur_func.add_bblock(val2ptr(address, ptr_size))
					self.cur_bb.targets.add(bb)
					return opcodes.PYBFD_DISASM_STOP

				if insn_type == opcodes.InstructionType.COND_BRANCH:
					self.cur_bb.end = val2ptr(address + size, ptr_size)
					next_bb = self.cur_func.add_bblock(val2ptr(address + size, ptr_size))
					bb = self.cur_func.add_bblock(target)

					self.cur_bb.targets.add(bb)
					self.cur_bb.targets.add(next_bb)
					self.cur_bb.instrs.append(InstrJCond(self.cur_bb,
									address,
									disassembly,
									target,
									size, binbytes))
					self.cur_bb = next_bb

					if next_bb in self.cur_func.new_bblocks:
						self.cur_func.new_bblocks.remove(next_bb)
						self.cur_func.bblocks.append(next_bb)

				elif insn_type == opcodes.InstructionType.JSR:
					if isinstance(arg1, OpLoad):
						target_addr = arg1.addr.get_val()
						if target_addr in rel_entries:
							self.cur_bb.instrs.append(InstrCall(self.cur_bb,
											address,
											disassembly,
											rel_entries[target_addr],
											size, binbytes))
						elif target_addr:
							self.add_entry(val2ptr(target_addr, ptr_size))
							self.cur_bb.instrs.append(InstrCall(self.cur_bb,
											address,
											disassembly,
											target_addr,
											size, binbytes))

					elif target:
						self.add_entry(val2ptr(target, ptr_size))
						self.cur_bb.instrs.append(InstrCall(self.cur_bb,
										address,
										disassembly,
										target,
										size, binbytes))

				elif insn_type == opcodes.InstructionType.COND_JSR:
					if isinstance(arg1, OpLoad):
						target_addr = arg1.addr.get_val()
						if target_addr in rel_entries:
							self.cur_bb.instrs.append(InstrCall(self.cur_bb,
											address,
											disassembly,
											rel_entries[target_addr],
											size, binbytes))
						elif target_addr:
							self.add_entry(val2ptr(target_addr, ptr_size))
							self.cur_bb.instrs.append(InstrCall(self.cur_bb,
											address,
											disassembly,
											target_addr,
											size, binbytes))

					elif target:
						self.add_entry(val2ptr(target, ptr_size))
						self.cur_bb.instrs.append(InstrCall(self.cur_bb,
										address,
										disassembly,
										target,
										size, binbytes))

				elif insn_type == opcodes.InstructionType.NON_BRANCH:
					if insn == 'mov':
						if isinstance(arg1, OpReg):
							self.cur_bb.instrs.append(InstrMov(self.cur_bb,
											address,
											disassembly,
											arg1.reg, arg2,
											size, binbytes))
						else:
							self.cur_bb.instrs.append(Instr(self.cur_bb,
											address,
											disassembly,
											size, binbytes))

					elif insn == 'lea':
						if arg2.val:
							if arg2.val >= self.start and arg2.val < self.end:
								self.add_entry(val2ptr(arg2.val, ptr_size))

						self.cur_bb.instrs.append(InstrCall(self.cur_bb,
										address,
										disassembly,
										arg2,
										size, binbytes))

					else:
						self.cur_bb.instrs.append(Instr(self.cur_bb,
										address,
										disassembly,
										size, binbytes))

			except Exception as e:
				traceback.print_exc()
				return opcodes.PYBFD_DISASM_STOP

			return opcodes.PYBFD_DISASM_CONTINUE

		def start_process(self, content):
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

				self.cur_func = Func(next)
				self.cur_func.add_bblock(next)
				self.entries.remove(next)

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

	codes = CodeOpcodes(bfd)
	codes.dynsyms = dynsyms

	for sym_addr in dynsyms.keys():
		# Only look at global functions
		flags = dynsyms[sym_addr].flags
		if SymbolFlags.GLOBAL not in flags:
			continue
		if SymbolFlags.FUNCTION not in flags:
			continue
		if sym_addr:
			codes.add_entry(sym_addr)

	if entry_addr:
		codes.add_entry(entry_addr)

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
		codes.set_range(sec.vma, sec.vma + sec.size)
		codes.start_process(content)

	def Func_cmp(x, y):
		return cmp(x.entry, y.entry)

	codes.funcs = sorted(codes.funcs, Func_cmp)

	return codes

def analysis_binary_instr(sql, binary, pkg_id, bin_id):
	codes = get_callgraph(binary)

	condition = 'pkg_id=' + Table.stringify(pkg_id) + ' and bin_id=' + Table.stringify(bin_id)
	condition_unknown = condition + ' and known=False'
	sql.delete_record(tables['binary_call'], condition)
	sql.delete_record(tables['binary_call_unknown'], condition_unknown)
	sql.delete_record(tables['binary_opcode_usage'], condition)

	class InstrSizes:
		def __init__(self, size):
			self.sizes = dict()
			sizes[size] = 1

		def get_count(self, size):
			return self.sizes[size]

		def increment_count(self, size):
			if size in self.sizes:
					self.sizes[size] = self.sizes[size] + 1
			else:
					self.sizes[size] = 1

		def get_sizes(self):
			return self.sizes.items()

	for func in codes.funcs:
		opcodes = dict()
		calls = []
		mnems = dict()
		prefixes = dict()

		for bb in func.bblocks:
			for instr in bb.instrs:
				if isinstance(instr, InstrCall):
					if isinstance(instr.target, int) or isinstance(instr.target, long):
						if not instr.target in calls:
							calls.append(instr.target)
					elif isinstance(instr.target, Op) and instr.target.val:
						if not instr.target.val in calls:
							calls.append(instr.target.val)

				opcode == instr.opcode
				size = instr.size

				if opcode == '':
					continue
				if (opcode, size) in opcodes:
					opcodes[(opcode, size)] = opcodes[(opcode, size)] + 1
				else:
					opcodes[(opcode, size)] = 1

				if (opcode, size) not in mnems:
					mnems[(opcode, size)] = set()
				mnems[(opcode,size)].add(instr.get_instr())

				if instr.prefixes == '':
					continue
				if instr.prefixes in prefixes:
					prefixes[instr.prefixes] = prefixes[instr.prefixes] + 1
				else:
					prefixes[instr.prefixes] = 1


		for call in calls:
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['func_addr'] = func.entry
			if isinstance(call, int) or isinstance(call, long):
				values['call_addr'] = call
			else:
				for addr, sym in codes.dynsyms.items():
					if sym.name == call:
						values['call_addr'] = sym.value
						break
				values['call_name'] = call
			sql.append_record(tables['binary_call'], values)

		for (opcode, size), count in opcodes.items():
			values = dict()
			values['pkg_id'] = pkg_id
			values['bin_id'] = bin_id
			values['func_addr'] = func.entry
			values['opcode'] = int(opcode.encode('hex'), 16)
			values['size'] = size
			values['count'] = count
			sql.append_record(tables['binary_opcode_usage'], values)

		for (opcode, size), mnem_set in mnems.items():
			values = dict()
			values['opcode'] = opcode
			values['size'] = size
			for mnem in mnem_set:
				values['mnem'] = mnem
				sql.append_record(tables['instr_list'], values)

		for prefix, count in prefixes.items():
			values = dict()
			values['prefix'] = prefix
			values['count'] = count
			sql.append_record(tables['prefixe_counts'], values)


if __name__ == "__main__":
	codes = get_callgraph(sys.argv[1])

	for func in codes.funcs:
		print "func %x:" % (func.entry)

		opcodes = dict()
		calls = []
		mnems = dict()
		prefixes = dict()

		for bb in func.bblocks:
			for instr in bb.instrs:
				if isinstance(instr, InstrCall):
					if isinstance(instr.target, int) or isinstance(instr.target, long) or isinstance(instr.target, str):
						if not instr.target in calls:
							calls.append(instr.target)
					elif isinstance(instr.target, Op) and instr.target.val:
						if not instr.target.val in calls:
							calls.append(instr.target.val)

				print instr.get_instr(),
				for item in instr.prefixes:
					print item.encode('hex'),
				print instr.opcode.encode('hex'), instr.size

				opcode = instr.opcode
				size = instr.size

				if opcode == '':
					continue
				if (opcode, size) in opcodes:
					opcodes[(opcode, size)] = opcodes[(opcode, size)] + 1
				else:
					opcodes[(opcode, size)] = 1

				if (opcode, size) not in mnems:
					mnems[(opcode, size)] = set()
				mnems[(opcode,size)].add(instr.get_instr())

				if instr.prefixes == '':
					continue
				if instr.prefixes in prefixes:
					prefixes[instr.prefixes] = prefixes[instr.prefixes] + 1
				else:
					prefixes[instr.prefixes] = 1

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

		for opcode, count in opcodes.items():
			print "    %4d %s %d" % (count, opcode[0].encode('hex'), opcode[1])
		print "mnems:"
		for (opcode, size), mnem_set in mnems.items():
			for mnem in mnem_set:
				print opcode.encode('hex'), size, mnem
		print "prefixes:"
		for prefix, count in prefixes.items():
			print prefix.encode('hex'), count

	print "-----------"
	print "Dynamic Symbols: %d" % (len(codes.dynsyms))
	print "Functions: %d" % (codes.nfuncs)
	print "Basic Blocks: %d" % (codes.nbblocks)
