\copy (SELECT syscall, name, get_pop(popularity), get_pop(popularity_with_libc) FROM syscall_popularity inner join syscall on syscall = number and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, syscall) TO '/tmp/syscall-popularity.csv' WITH CSV
\echo 'Output to /tmp/syscall-popularity.csv'

\copy (SELECT syscall, name, get_pop(popularity), get_pop(popularity_with_libc) FROM syscall_popularity_by_vote inner join syscall on syscall = number and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, syscall) TO '/tmp/syscall-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/syscall-popularity-by-vote.csv'

\copy (SELECT number, name FROM syscall WHERE not exists (select * from syscall_popularity where syscall = number) ORDER BY syscall) TO '/tmp/syscall-unused.csv' WITH CSV
\echo 'Output to /tmp/syscall-unused.csv'
