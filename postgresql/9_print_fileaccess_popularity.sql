\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity WHERE file like '/dev%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/dev-popularity.csv' WITH CSV
\echo 'Output to /tmp/dev-popularity.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity_by_vote WHERE file like '/dev%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/dev-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/dev-popularity-by-vote.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity WHERE file like '/proc%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/proc-popularity.csv' WITH CSV
\echo 'Output to /tmp/proc-popularity.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity_by_vote WHERE file like '/proc%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/proc-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/proc-popularity-by-vote.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity WHERE file like '/sys%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/sys-popularity.csv' WITH CSV
\echo 'Output to /tmp/sys-popularity.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity_by_vote WHERE file like '/sys%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/sys-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/sys-popularity-by-vote.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity WHERE file like '/etc%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/etc-popularity.csv' WITH CSV
\echo 'Output to /tmp/etc-popularity.csv'

\copy (SELECT file, get_pop(popularity), get_pop(popularity_with_libc) FROM fileaccess_popularity_by_vote WHERE file like '/etc%' and (popularity > 0.000001 or popularity_with_libc > 0.000001) ORDER BY popularity DESC, file) TO '/tmp/etc-popularity-by-vote.csv' WITH CSV
\echo 'Output to /tmp/etc-popularity-by-vote.csv'
