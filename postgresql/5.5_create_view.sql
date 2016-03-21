CREATE OR REPLACE VIEW binary_syscall_array AS
 SELECT binary_syscall.bin_id,
    array_agg(DISTINCT binary_syscall.syscall) AS syscalls
   FROM binary_syscall
  GROUP BY binary_syscall.bin_id;

CREATE OR REPLACE VIEW executable_syscall_array AS
 SELECT executable_syscall.bin_id,
    array_agg(DISTINCT executable_syscall.syscall) AS syscalls
   FROM executable_syscall
  GROUP BY executable_syscall.bin_id;

CREATE OR REPLACE VIEW syscall_footprint AS
 SELECT array_length(array_agg(t2.binary_name), 1) AS total,
    t1.syscalls AS footprint,
    array_agg(t2.binary_name) AS exe_list
   FROM executable_syscall_array t1,
    binary_id t2
  WHERE t2.id = t1.bin_id
  GROUP BY t1.syscalls
  ORDER BY array_length(array_agg(t2.binary_name), 1) DESC;


CREATE OR REPLACE VIEW package_syscall_array AS
 SELECT package_syscall.pkg_id,
    array_agg(DISTINCT package_syscall.syscall) AS syscalls
   FROM package_syscall
  GROUP BY package_syscall.pkg_id;

CREATE OR REPLACE VIEW package_call_array AS
 SELECT package_call.pkg_id,
    package_call.dep_bin_id,
    array_agg(DISTINCT libc_symbol.symbol_name) AS calls
   FROM package_call
   JOIN libc_symbol
   ON   package_call.dep_bin_id = libc_symbol.bin_id
   AND  package_call.call = libc_symbol.func_addr
  WHERE EXISTS (
   SELECT * FROM libc_real_symbol WHERE
   libc_real_symbol.symbol_name = libc_symbol.symbol_name
  )
  GROUP BY package_call.pkg_id, package_call.dep_bin_id;
