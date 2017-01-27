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
		self.opcode, self.prefixes = get_x86_opcodes(binbytes)

	def __str__(self):
		return "%x:        (%s)" % (self.addr, self.dism)

	def get_instr(self):
		splitdism = self.dism.split()
		if splitdism[0] == 'repz' or splitdism[0] == "rep" or splitdism[0] == "repnz":
			return (splitdism[0]+" "+splitdism[1])
		if splitdism[0] == "lock":
			return splitdism[1]
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
		if regval and str(self.reg) in regval.keys() and isinstance(regval[str(self.reg)], (int, long)):
			return regval[str(self.reg)] & self.mask
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

def insert_into_db(func, sql, pkg_id, bin_id):
	if sql == None or pkg_id == None or bin_id == None:
		logging.info("sql, pkg_id or bin_id was None??")
		traceback.print_exec()

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

def get_callgraph(binary_name, sql=None, pkg_id=None, bin_id=None):

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
			# self.nbblocks = 0
			self.regval = {}

		def set_range(self,start, end):
			self.start = start
			self.end = end

		def set_regval(self, reg, val):
			if reg in self.regval.keys():
				# do something to save old_val?
				self.regval[reg] = val
			else:
				self.regval[reg] = val

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
			#print insn_type,
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
							if arith:
								op = OpArith(OpReg(r, mask), Op(off), OpArith.ADD)
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
						elif self.regset.is_reg(arg1):
							(r, _, mask) = self.regset.index_reg(arg1)
							if r != None and mask !=None:
								arg1 = OpReg(r, mask)
						#else:
						#	logging.info(arg1)
						#	logging.info('what to do with this?')

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
						elif self.regset.is_reg(arg2):
							(r, _, mask) = self.regset.index_reg(arg2)
							if r != None and mask != None:
								arg2 = OpReg(r, mask)
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


				if insn_type == opcodes.InstructionType.JSR or insn_type == opcodes.InstructionType.COND_JSR: #CALL
					target_addr = None
					if insn == 'call':
						self.cur_func.num_calls += 1
					if isinstance(arg1, OpLoad):
						target_addr = arg1.addr.get_val()
					elif isinstance(arg1, OpReg):
						target_addr = arg1.get_val(self.regval)
					if target_addr:
						if target_addr > 0xff and target_addr < 0x80000000:
							if target_addr in rel_entries:
								self.cur_func.instrs.append(InstrCall(address,
											disassembly,
											rel_entries[target_addr],
											size, binbytes))
							else:
								self.add_entry(val2ptr(target_addr, ptr_size))
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
						self.add_entry(val2ptr(target, ptr_size))
						self.cur_func.instrs.append(InstrCall(address,
											disassembly,
											target, size, binbytes))
					else:
						if insn == 'call':
							self.cur_func.num_missed_calls += 1

				elif insn_type == opcodes.InstructionType.NON_BRANCH:
					if insn == 'mov':
						if isinstance(arg1, OpReg):
							self.cur_func.instrs.append(InstrMov(address,
											disassembly,
											arg1.reg, arg2,
											size, binbytes))
							if isinstance(arg2,Op) and not isinstance(arg2,OpLoad):
								self.set_regval(str(arg1.reg), arg2.get_val())
						else:
							self.cur_func.instrs.append(Instr(address,
											disassembly,
											size, binbytes))

					elif insn == 'lea':
						if isinstance(arg1, OpReg):
							self.cur_func.instrs.append(InstrMov(address,
											disassembly,
											arg1.reg, arg2,
											size, binbytes))
							if isinstance(arg2,Op):
								self.set_regval(str(arg1.reg), arg2.get_val())
						else:
							self.cur_func.instrs.append(Instr(address,
										disassembly,
										size, binbytes))

					else:
						self.cur_func.instrs.append(Instr(address, disassembly, size, binbytes))
				else:
					self.cur_func.instrs.append(Instr(address, disassembly, size, binbytes))

			except Exception as e:
				traceback.print_exc()
				return opcodes.PYBFD_DISASM_STOP

			return opcodes.PYBFD_DISASM_CONTINUE

		def start_process(self, content, dynsym_list, sql,  pkg_id, bin_id):
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

				# self.funcs.append(self.cur_func)
				insert_into_db(self.cur_func, sql, pkg_id, bin_id)
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
		if is_hex(size):
			size = int(size, 16)
		dynsym_list[addr] = size

	if process.wait() != 0:
		raise Exception('process failed: readelf --dyn-syms')

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
		codes.start_process(content, dynsym_list, sql, pkg_id, bin_id)

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

	get_callgraph(binary, sql, pkg_id, bin_id)

if __name__ == "__main__":
	codes = get_callgraph(sys.argv[1])

	for func in codes.funcs:
		print "-------------"
		print "func %x:" % (func.start)

		opcodes = dict()
		calls = []

		for instr in func.instrs:
			if isinstance(instr, InstrCall):
				if isinstance(instr.target, int) or isinstance(instr.target, long) or isinstance(instr.target, str):
					if not instr.target in calls:
						calls.append(instr.target)
				elif isinstance(instr.target, Op) and instr.target.val:
					if not instr.target.val in calls:
						calls.append(instr.target.val)

			#print instr.get_instr(),
			#for item in instr.prefixes:
			#	print item.encode('hex'),
			#print instr.opcode.encode('hex'), instr.size

			opcode = instr.opcode
			size = instr.size
			prefix = instr.prefixes
			mnem = instr.get_instr()

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

		for (prefix, opcode, size, mnem), count in opcodes.items():
			print prefix.encode('hex'), opcode.encode('hex'), size, mnem, count

	print "-----------"
	print "Dynamic Symbols: %d" % (len(codes.dynsyms))
	print "Functions: %d" % (codes.nfuncs)
	# print "Basic Blocks: %d" % (codes.nbblocks)
