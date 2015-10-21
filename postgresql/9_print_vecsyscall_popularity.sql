\copy (SELECT request, get_pop(popularity), get_pop(popularity_with_libc) FROM vecsyscall_popularity WHERE syscall = 72 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/fcntl-popularity.csv' WITH CSV
\echo 'Output to /tmp/fcntl-popularity.csv'

\copy (SELECT request, get_pop(popularity), get_pop(popularity_with_libc) FROM vecsyscall_popularity_by_vote WHERE syscall = 72 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/fcntl-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/fcntl-popularity-by-vote.csv'

\copy (SELECT request, get_pop(popularity), get_pop(popularity_with_libc) FROM vecsyscall_popularity WHERE syscall = 16 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/ioctl-popularity.csv' WITH CSV
\echo 'Output to /tmp/ioctl-popularity.csv'

\copy (SELECT request, get_pop(popularity), get_pop(popularity_with_libc) FROM vecsyscall_popularity_by_vote WHERE syscall = 16 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/ioctl-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/ioctl-popularity-by-vote.csv'

\copy (SELECT request, get_pop(popularity), get_pop(popularity_with_libc) FROM vecsyscall_popularity WHERE syscall = 157 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/prctl-popularity.csv' WITH CSV
\echo 'Output to /tmp/prctl-popularity.csv'

\copy (SELECT request, get_pop(popularity), get_pop(popularity_with_libc) FROM vecsyscall_popularity_by_vote WHERE syscall = 157 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/prctl-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/prctl-popularity-by-vote.csv'
