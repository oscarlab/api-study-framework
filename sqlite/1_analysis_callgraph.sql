drop table if exists binary_call_result;
create table binary_call_result (binary text not null, func text not null, target text not null, primary key (binary, func, target));
with recursive
callgraph(binary, func, target) as (
select binary, func, target from binary_call as b where exists (select * from binary_list where binary = b.binary and type = 'lib')
union
select b1.binary, b1.func, b2.target from callgraph as b1 join binary_call as b2 on b1.binary = b2.binary and b1.target = b2.func and b2.target not null where exists (select * from binary_list where binary = b1.binary and type = 'lib')
)
insert into binary_call_result select * from callgraph;
