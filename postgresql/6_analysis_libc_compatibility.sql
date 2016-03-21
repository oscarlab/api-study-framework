CREATE OR REPLACE FUNCTION filter_call(call VARCHAR)
RETURNS VARCHAR AS $$
BEGIN
	call := regexp_replace(call, '__(.+)_chk', '\1');
	call := regexp_replace(call, '__assert(_fail)?', 'assert');
	call := regexp_replace(call, '__isoc99_(.+)', '\1');
	call := replace(call, '__open_2', 'open');
	call := replace(call, '__openat_2', 'openat');
	call := replace(call, '__ctype_get_mb_cur_max', 'MB_CUR_MAX');
	call := replace(call, '_stdlib_mb_cur_max', 'MB_CUR_MAX');
	RETURN call;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION filter_calls(calls VARCHAR[])
RETURNS VARCHAR[] AS $$
BEGIN
	RETURN ARRAY (SELECT filter_call(call) FROM unnest(calls) AS call);
END
$$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION analysis_call_compatibility(
	lib INT,
	support_calls VARCHAR[]
)
RETURNS FLOAT AS $$

DECLARE
	compat FLOAT;
	total_compat FLOAT;

BEGIN
	compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_call_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.dep_bin_id = lib AND t1.calls <@ support_calls
	);
	
	total_compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_call_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.dep_bin_id = lib
	);

	compat := (SELECT COALESCE(MAX(compat), 0));

	RAISE NOTICE '% / % = %', compat, total_compat, compat / total_compat;

	RETURN compat / total_compat;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_call_compatibility_filtered(
	lib INT,
	support_calls VARCHAR[]
)
RETURNS FLOAT AS $$

DECLARE
	compat FLOAT;
	total_compat FLOAT;

BEGIN
	compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_call_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.dep_bin_id = lib AND filter_calls(t1.calls) <@ support_calls
	);
	
	total_compat := (
		SELECT sum(get_pop(t2.inst)) FROM package_call_array AS t1
		JOIN package_inst AS t2 ON t1.pkg_id = t2.pkg_id
		WHERE t1.dep_bin_id = lib
	);

	compat := (SELECT COALESCE(MAX(compat), 0));

	RAISE NOTICE '% / % = %', compat, total_compat, compat / total_compat;

	RETURN compat / total_compat;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION analysis_call_progress(lib INT)
RETURNS SETOF FLOAT AS $$

DECLARE
	calls VARCHAR[];
	c VARCHAR;

BEGIN
	FOR c IN (
		SELECT call FROM call_popularity
		WHERE bin_id = lib
		ORDER BY popularity DESC
	) LOOP
		calls := calls || c;
		RAISE NOTICE 'analyze % (%)', c, array_length(calls, 1);
		RETURN NEXT (
			SELECT analysis_call_compatibility(lib, calls)
		);
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
