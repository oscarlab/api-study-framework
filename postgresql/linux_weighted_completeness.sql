CREATE OR REPLACE FUNCTION linux_weighted_completeness(
	api_types SMALLINT[], apis api_pair[]
)
RETURNS FLOAT AS $$

DECLARE
	pkg_apis RECORD;
	comp FLOAT := 0.0;
	total_comp FLOAT := 0.0;

BEGIN
	FOR pkg_apis IN (
		SELECT t2.percent_order, t1.apis FROM (
			SELECT p.pkg_id, array_accum(p.apis) AS apis
			FROM package_api_usage_array AS p
			WHERE ARRAY[p.api_type] <@ api_types
			GROUP BY p.pkg_id
		) AS t1 JOIN package_install AS t2
		ON t1.pkg_id = t2.pkg_id
	) LOOP
		IF pkg_apis.apis <@ apis THEN
			comp := comp + pkg_apis.percent_order;
		END IF;
		total_comp := total_comp + pkg_apis.percent_order;
	END LOOP;

	RETURN (SELECT COALESCE(MAX(comp), 0)) / total_comp;
END
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION linux_weighted_completeness_improvement(
	api_types SMALLINT[], apis api_pair[], more_apis INTEGER
)
RETURNS SETOF api_improvement AS $$

DECLARE
	api RECORD;

BEGIN
	RETURN NEXT (SELECT ROW(null::smallint, null::bigint, linux_weighted_completeness(api_types, apis)));

	FOR api IN (
		SELECT api_type, api_id
		FROM api_importance
		WHERE ARRAY[api_type] <@ api_types AND
		NOT ARRAY[ROW(api_type, api_id)::api_pair] <@ apis
		ORDER BY api_importance_order DESC
		LIMIT more_apis
	) LOOP
		apis := apis || ROW(api.api_type, api.api_id)::api_pair;
		RETURN NEXT (SELECT ROW(
				api.api_type,
				api.api_id,
				linux_weighted_completeness(api_types, apis)
			));
	END LOOP;
	RETURN;
END
$$ LANGUAGE plpgsql;


