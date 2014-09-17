select r.syscall, s.name, count(r.syscall)*100/(select count(binary) from binary_list where type='exe') as percentage
from recursive_syscall_result as r join syscall as s
on r.syscall = s.number
group by syscall order by percentage desc;
