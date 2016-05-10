CREATE OR REPLACE VIEW package_instr_usage_array AS
	SELECT pkg_id, array_agg(instr) AS instrs
	FROM package_instr_usage
	GROUP BY pkg_id;

CREATE OR REPLACE FUNCTION x86_weighted_completeness(
	instrs VARCHAR(15)[]
)
RETURNS FLOAT AS $$

DECLARE
	pkg_instrs RECORD;
	comp FLOAT := 0.0;
	total_comp FLOAT := 0.0;

BEGIN
	FOR pkg_instrs IN (
		SELECT t2.percent_order, t1.instrs FROM
		package_instr_usage_array AS t1
		JOIN
		package_install AS t2
		ON t1.pkg_id = t2.pkg_id
	) LOOP
		IF pkg_instrs.instrs <@ instrs THEN
			comp := comp + pkg_instrs.percent_order;
		END IF;
		total_comp := total_comp + pkg_instrs.percent_order;
	END LOOP;

	RETURN (SELECT COALESCE(MAX(comp), 0)) / total_comp;
END
$$ LANGUAGE plpgsql;

DO $$
BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'instr_improvement') THEN
		CREATE TYPE instr_improvement AS (
			instr VARCHAR(15),
			weighted_completeness FLOAT
		);
	END IF;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION x86_weighted_completeness_improvement(
	instrs VARCHAR(15)[], more_instrs INTEGER
)
RETURNS SETOF instr_improvement AS $$

DECLARE
	instr RECORD;

BEGIN
	RETURN NEXT (SELECT ROW(null::VARCHAR(15), x86_weighted_completeness(instrs)));

	FOR instr IN (
		SELECT t.instr
		FROM instr_importance AS t
		WHERE NOT ARRAY[t.instr] <@ instrs
		ORDER BY t.instr_importance_order DESC
		LIMIT more_instrs
	) LOOP
		instrs := instrs || ARRAY[instr];
		RETURN NEXT (SELECT ROW(
				instr,
				linux_weighted_completeness(instrs)
			));
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
