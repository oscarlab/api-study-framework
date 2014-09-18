drop table if exists binary_dependency_result;
create table binary_dependency_result (binary text not null, symbol text not null, dependency text not null, primary key (binary, symbol, dependency));
insert into binary_dependency_result
select bs1.binary, bs1.name as symbol, bs2.binary as dependency from
binary_symbol as bs1
join binary_symbol as bs2 on bs1.name=bs2.name and bs1.defined='False' and bs2.defined='True'
join binary_dependency as bd on bs1.binary=bd.binary
join binary_result as br on br.name=bd.dependency and br.binary=bs2.binary
group by bs1.binary, bs1.name, bs2.binary;
