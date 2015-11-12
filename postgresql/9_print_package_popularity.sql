\copy (SELECT t1.package_name, inst, vote FROM package_popularity AS t1 JOIN package_id AS t2 ON t1.package_name = t2.package_name WHERE EXISTS (SELECT * FROM package_syscall WHERE pkg_id = t2.id)) TO '/tmp/package-popularity.csv' WITH CSV HEADER
\echo 'Output to /tmp/package-popularity.csv'
