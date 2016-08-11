CREATE OR REPLACE VIEW package_opcode_usage_array AS
	SELECT pkg_id, array_agg(opcode) AS opcodes
	FROM package_opcode_usage
	GROUP BY pkg_id;

CREATE OR REPLACE FUNCTION x86_weighted_completeness(
	opcodes BIGINT[]
)
RETURNS FLOAT AS $$

DECLARE
	pkg_opcodes RECORD;
	comp FLOAT := 0.0;
	total_comp FLOAT := 0.0;

BEGIN
	FOR pkg_opcodes IN (
		SELECT t2.percent_order, t1.opcodes FROM
		package_opcode_usage_array AS t1
		JOIN
		package_install AS t2
		ON t1.pkg_id = t2.pkg_id
	) LOOP
		IF pkg_opcodes.opcodes <@ opcodes THEN
			comp := comp + pkg_opcodes.percent_order;
		END IF;
		total_comp := total_comp + pkg_opcodes.percent_order;
	END LOOP;

	RETURN (SELECT COALESCE(MAX(comp), 0)) / total_comp;
END
$$ LANGUAGE plpgsql;

DO $$
BEGIN
	IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'opcode_improvement') THEN
		CREATE TYPE opcode_improvement AS (
			opcode BIGINT,
			weighted_completeness FLOAT
		);
	END IF;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION x86_weighted_completeness_improvement(
	opcodes BIGINT[], more_opcodes INTEGER
)
RETURNS SETOF opcode_improvement AS $$

DECLARE
	opcode RECORD;

BEGIN
	RETURN NEXT (SELECT ROW(null::INT, x86_weighted_completeness(opcodes)));

	FOR opcode IN (
		SELECT t.opcode
		FROM opcode_importance AS t
		WHERE NOT ARRAY[t.opcode] <@ opcodes
		ORDER BY t.opcode_importance_order DESC
		LIMIT more_opcodes
	) LOOP
		opcodes := opcodes || ARRAY[opcode.opcode];

		RAISE NOTICE 'add % (%)', opcode.opcode, array_length(opcodes, 1);

		RETURN NEXT (SELECT ROW(
				opcode.opcode,
				x86_weighted_completeness(opcodes)
			));
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;
