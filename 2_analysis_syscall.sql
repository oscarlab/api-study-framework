drop table if exists symbol_syscall_result;
create table symbol_syscall_result (binary text not null, symbol text not null, syscall int not null, primary key (binary, symbol, syscall));
with symbol_call (binary, symbol, target)
as (
select r.binary, r.func as symbol, r.target from binary_call_result r where
exists (select * from binary_symbol where binary=r.binary and name=r.func)
)
insert into symbol_syscall_result
select b.binary, b.symbol, s.syscall from symbol_call as b join binary_syscall as s on b.symbol = s.func
union
select b.binary, b.symbol, s.syscall from symbol_call as b join binary_syscall as s on b.target = s.func;
