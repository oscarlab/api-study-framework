\copy (SELECT t2.name AS reqeust, get_pop(popularity) AS popularity, get_pop(popularity_with_libc) AS popularity_with_libc FROM vecsyscall_popularity AS t1 JOIN vecsyscall AS t2 ON t1.syscall = t2.syscall AND t1.request = t2.code WHERE t1.syscall = 72 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/fcntl-popularity.csv' WITH CSV HEADER
\echo 'Output to /tmp/fcntl-popularity.csv'

\copy (SELECT t2.name AS request, get_pop(popularity) AS popularity, get_pop(popularity_with_libc) AS popularity_with_libc FROM vecsyscall_popularity_by_vote AS t1 JOIN vecsyscall AS t2 ON t1.syscall = t2.syscall AND t1.request = t2.code WHERE t1.syscall = 72 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/fcntl-popularity-by-vote.csv' WITH CSV HEADER
\echo 'Output to /tmp/fcntl-popularity-by-vote.csv'

\copy (SELECT t2.name AS request, get_pop(popularity) AS popularity, get_pop(popularity_with_libc) AS popularity_with_libc FROM vecsyscall_popularity AS t1 JOIN vecsyscall AS t2 ON t1.syscall = t2.syscall AND t1.request = t2.code WHERE t1.syscall = 16 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/ioctl-popularity.csv' WITH CSV HEADER
\echo 'Output to /tmp/ioctl-popularity.csv'

\copy (SELECT t2.name AS request, get_pop(popularity) AS popularity, get_pop(popularity_with_libc) AS popularity_with_libc FROM vecsyscall_popularity_by_vote AS t1 JOIN vecsyscall AS t2 ON t1.syscall = t2.syscall AND t1.request = t2.code WHERE t1.syscall = 16 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/ioctl-popularity-by-vote.csv' WITH CSV HEADER
\echo 'Output to /tmp/ioctl-popularity-by-vote.csv'

\copy (SELECT t2.name AS request, get_pop(popularity) AS popularity, get_pop(popularity_with_libc) AS popularity_with_libc FROM vecsyscall_popularity AS t1 JOIN vecsyscall AS t2 ON t1.syscall = t2.syscall AND t1.request = t2.code WHERE t1.syscall = 157 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/prctl-popularity.csv' WITH CSV HEADER
\echo 'Output to /tmp/prctl-popularity.csv'

\copy (SELECT t2.name AS request, get_pop(popularity) AS popularity, get_pop(popularity_with_libc) AS popularity_with_libc FROM vecsyscall_popularity_by_vote AS t1 JOIN vecsyscall AS t2 ON t1.syscall = t2.syscall AND t1.request = t2.code WHERE t1.syscall = 157 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/prctl-popularity-by-vote.csv' WITH CSV HEADER
\echo 'Output to /tmp/prctl-popularity-by-vote.csv'
