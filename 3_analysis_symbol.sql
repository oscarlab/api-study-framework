drop table if exists symbol_call_result;
create table symbol_call_result (binary text not null, symbol text not null, target text not null, primary key (binary, symbol, target));
insert into symbol_call_result
select r.binary, r.func as symbol, r.target from binary_call_result r where
exists (select * from binary_symbol where binary=r.binary and name=r.func)
and
exists (select * from binary_symbol where binary=r.binary and name=r.target);
