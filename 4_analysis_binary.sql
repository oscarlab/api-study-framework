drop table if exists binary_result;
create table binary_result (name text not null, package text not null, binary text not null, type text not null);
insert into binary_result
select substr(l.link,length(trim(l.link, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_'))+1) as name, b.real_package as package, b.binary, b.type from binary_link as l join binary_list as b on l.target = b.binary
union all
select substr(binary,length(trim(binary, 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_'))+1) as name, real_package as package, binary, type from binary_list;
