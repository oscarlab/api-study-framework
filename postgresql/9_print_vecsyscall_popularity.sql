\copy (SELECT request, popularity, popularity_with_libc - popularity FROM vecsyscall_popularity WHERE syscall = 72 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/fcntl-popularity.csv' WITH CSV
\echo 'Output to /tmp/fcntl-popularity.csv'

\copy (SELECT request, popularity, popularity_with_libc - popularity FROM vecsyscall_popularity WHERE syscall = 16 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/ioctl-popularity.csv' WITH CSV
\echo 'Output to /tmp/fcntl-popularity.csv'

\copy (SELECT request, popularity, popularity_with_libc - popularity FROM vecsyscall_popularity WHERE syscall = 157 and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, request) TO '/tmp/prctl-popularity.csv' WITH CSV
\echo 'Output to /tmp/fcntl-popularity.csv'

