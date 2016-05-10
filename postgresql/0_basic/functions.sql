-- table_exists(name):
-- check if a table exists in the database

CREATE OR REPLACE FUNCTION table_exists(name VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
	IF EXISTS (
		SELECT relname FROM pg_class WHERE relname=name
	) THEN
		RETURN True;
	END IF;
	RETURN False;
END
$$ LANGUAGE plpgsql;

-- temp_table_exists(name):
-- check if a temporary table exists in the database

CREATE or REPLACE FUNCTION temp_table_exists(name VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
	/* check the table exist in database and is visible*/
	PERFORM n.nspname, c.relname
	FROM pg_catalog.pg_class c LEFT JOIN pg_catalog.pg_namespace n
	ON n.oid = c.relnamespace
	where n.nspname like 'pg_temp_%'
	AND pg_catalog.pg_table_is_visible(c.oid)
	AND Upper(relname) = Upper(name);

	IF FOUND THEN
		RETURN TRUE;
	ELSE
		RETURN FALSE;
	END IF;
END
$$ LANGUAGE plpgsql;

-- get_package_name(id):
-- get packagename from package id

CREATE or REPLACE FUNCTION get_package_name(p INT)
RETURNS VARCHAR AS $$
BEGIN
	RETURN (SELECT package_name FROM package_id WHERE id = p);
END
$$ LANGUAGE plpgsql;

-- get_binary_name(id):
-- get binary name from binary id

CREATE or REPLACE FUNCTION get_binary_name(b INT)
RETURNS VARCHAR AS $$
BEGIN
	RETURN (SELECT binary_name FROM binary_id WHERE id = b);
END
$$ LANGUAGE plpgsql;

-- get_api_importance(order):
-- in the database we store log10(1 - API importance) for precision.
-- use this function to translate back to API importance

CREATE OR REPLACE FUNCTION get_api_importance(precent_order FLOAT)
RETURNS FLOAT AS $$
BEGIN
       IF precent_order > 6 THEN
               RETURN 1.0;
       ELSE
               RETURN 1.0 - 10.0 ^ (-percent_order);
       END IF;
END
$$ LANGUAGE plpgsql;
