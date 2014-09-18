drop table if exists recursive_syscall_result;
create table recursive_syscall_result (package text not null, binary text not null, syscall int not null, primary key (package, binary, syscall));
with recursive
binary_symbol_recursive (binary, symbol, dependency)
as
(
select * from binary_dependency_result
union all
select bsr.binary, bdr.symbol, bdr.dependency
from binary_symbol_recursive as bsr
join symbol_call_result as scr on bsr.dependency=scr.binary and bsr.symbol=scr.symbol
join binary_dependency_result as bdr on scr.binary=bdr.binary and scr.target=bdr.symbol
)
insert into recursive_syscall_result
select bl.real_package as package, bsr.binary, bs.syscall from
binary_symbol_recursive as bsr
join symbol_syscall_result as bs on bsr.dependency=bs.binary and bsr.symbol=bs.symbol
join binary_list as bl on bsr.binary=bl.binary and bl.type = 'exe'
union
select bl.real_package as package, bs.binary, bs.syscall
from binary_syscall as bs
join binary_list as bl on bs.binary=bl.binary and bl.type = 'exe'
group by bs.binary, bs.syscall;
