DO $$
BEGIN
IF NOT table_exists('binary_symbol_hash') THEN
	CREATE TABLE binary_symbol_hash (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		symbol INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, symbol)
	);
	CREATE INDEX binary_symbol_hash_pkg_id_bin_id_idx
		ON binary_symbol_hash (pkg_id, bin_id);
	CREATE INDEX binary_symbol_hash_pkg_id_bin_id_func_addr_idx
		ON binary_symbol_hash (pkg_id, bin_id, func_addr);
	CREATE INDEX binary_symbol_hash_symbol_idx
		ON binary_symbol_hash (symbol);
END IF;

IF NOT table_exists('library_call_hash') THEN
	CREATE TABLE library_call_hash (
		pkg_id INT NOT NULL, bin_id INT NOT NULL,
		func_addr INT NOT NULL,
		call INT NOT NULL,
		PRIMARY KEY (pkg_id, bin_id, func_addr, call)
	);
	CREATE INDEX library_call_hash_pkg_id_bin_id_idx
		ON library_call_hash (pkg_id, bin_id);
	CREATE INDEX library_call_hash_pkg_id_bin_id_func_addr_idx
		ON library_call_hash (pkg_id, bin_id, func_addr);
END IF;

END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION hash_binary(p INT, b INT)
RETURNS void AS $$
BEGIN
	INSERT INTO binary_symbol_hash
		SELECT p, b, func_addr, hashtext(symbol_name) FROM
		binary_symbol
		WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_call_hash
		SELECT p, b, func_addr, hashtext(call_name) FROM
		library_call
		WHERE pkg_id = p AND bin_id = b;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION hash_binary_distinct(p INT, b INT)
RETURNS void AS $$
BEGIN
	INSERT INTO binary_symbol_hash
		SELECT DISTINCT p, b, func_addr, hashtext(symbol_name) FROM
		binary_symbol
		WHERE pkg_id = p AND bin_id = b;
	INSERT INTO library_call_hash
		SELECT DISTINCT p, b, func_addr, hashtext(call_name) FROM
		library_call
		WHERE pkg_id = p AND bin_id = b;
END
$$ LANGUAGE plpgsql;
