DO $$
DECLARE
	libc_pkg_id INT := id FROM package_id WHERE package_name = 'libc6';
BEGIN

IF table_exists('libc_symbol') THEN
	DROP TABLE libc_symbol;
END IF;

CREATE TABLE libc_symbol AS
SELECT bin_id, func_addr, symbol_name FROM binary_symbol
WHERE pkg_id = libc_pkg_id and func_addr != 0;

END $$ LANGUAGE plpgsql;
