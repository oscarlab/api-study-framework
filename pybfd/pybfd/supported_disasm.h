
#ifndef __SUPPORTED_DISASM_H_
#define __SUPPORTED_DISASM_H_

#include "bfd_headers.h"

//
// Supported architectures
//
typedef struct _supported_disasm
{
    enum bfd_architecture   bfd_arch;
    disassembler_ftype      bfd_print_insn_endian_little;
    disassembler_ftype      bfd_print_insn_endian_big;
} supported_disasm, *p_supported_disasm;


supported_disasm p_supported_disasm_list[]= {
    {bfd_arch_i386, print_insn_i386, print_insn_i386},
    {bfd_arch_l1om, print_insn_i386, print_insn_i386},
    {bfd_arch_k1om, print_insn_i386, print_insn_i386}
};

#endif // __SUPPORTED_DISASM_H_
