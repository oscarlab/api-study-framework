#!/usr/bin/python

import sys

sys.path.append('pybfd/lib/python')
from pybfd import opcodes, bfd, section
from pybfd.opcodes import Opcodes, PYBFD_DISASM_STOP, OpcodesException
from pybfd.bfd import Bfd, BfdException

class DumpOpcodes(Opcodes):
	def __init__(self, bfd):
		Opcodes.__init__(self, bfd)
		self.all_opcodes = dict()

	def process_opcode(self, address, size, branch_delay_insn, insn_type, target, target2, disassembly):
		if not disassembly.startswith('(bad)'):
			self.all_opcodes[self.target] = disassembly
		return PYBFD_DISASM_STOP

# Initialize BFD instance
bfd = Bfd("/lib/x86_64-linux-gnu/libc.so.6")
opcodes = DumpOpcodes(bfd)

PREFIX = range(0x40, 0x50) + [0xf3, 0xf2, 0xf0, 0x2e, 0x36, 0x3e, 0x26] + range(0x64, 0x68)
TWOBYTE = [0x0f]
THREEBYTE = [0x38, 0x3a, 0x7a]

for byte1 in range(0x00, 0xff):
	if byte1 in PREFIX + TWOBYTE:
		continue
	content = chr(byte1) + '\x00' * 15
	opcodes.target = chr(byte1)
	opcodes.initialize_smart_disassemble(content, 0)
	opcodes.start_smart_disassemble(0, opcodes.process_opcode)

for byte1 in TWOBYTE:
	for byte2 in range(0x00, 0xff):
		if byte2 in THREEBYTE:
			continue

		content = chr(byte1) + chr(byte2) + '\x00' * 14
		opcodes.target = chr(byte1) + chr(byte2)
		opcodes.initialize_smart_disassemble(content, 0)
		opcodes.start_smart_disassemble(0, opcodes.process_opcode)

	for byte2 in THREEBYTE:
		for byte3 in range(0x00, 0xff):
			content = chr(byte1) + chr(byte2) + chr(byte3) + '\x00' * 13
			opcodes.target = chr(byte1) + chr(byte2) + chr(byte3)
			opcodes.initialize_smart_disassemble(content, 0)
			opcodes.start_smart_disassemble(0, opcodes.process_opcode)


for opcode in sorted(opcodes.all_opcodes.keys()):
	print "%s: %s" % (opcode.encode('hex'), opcodes.all_opcodes[opcode])
