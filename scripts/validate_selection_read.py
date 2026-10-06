"""Operator-only, aggregate read audit; no clinical contents or credentials printed.

Uses the configured restricted MCP reader. Does not modify data or invoke models.
Run in the target staging environment before enabling selection tools.
"""
import asyncio
import json

from intel_mcp.config import Settings
from intel_mcp.engine_database import DatabaseEngineClient


def audit(connection, _request):
    role = connection.execute("SELECT current_user, current_setting('transaction_read_only')").fetchone()
    schemas = connection.execute("""
        SELECT schema_version, count(*), count(DISTINCT eu_number)
        FROM mcp_serving.approved_profiles_v1 GROUP BY schema_version ORDER BY schema_version
    """).fetchall()
    counts = connection.execute("""
        SELECT count(*), count(DISTINCT eu_number) FROM mcp_serving.profile_filter_v1
    """).fetchone()
    missing = connection.execute("""
        SELECT count(*) FROM mcp_serving.profile_filter_v1 p
        WHERE NOT EXISTS (SELECT 1 FROM mcp_serving.approved_profiles_v1 a WHERE a.eu_number=p.eu_number)
    """).fetchone()[0]
    return {"reader_role": role[0], "transaction_read_only": role[1],
        "profile_schemas": [{"schema": s, "rows": n, "distinct_trials": d} for s, n, d in schemas],
        "filter_rows": counts[0], "filter_distinct_trials": counts[1], "filter_rows_without_profile": missing}


async def main():
    settings = Settings.from_environment()
    settings.validate_engine()
    if settings.engine_source != 'database':
        raise SystemExit('Database source required')
    client = DatabaseEngineClient(settings)
    try:
        result = await client._read(audit, {})
        print(json.dumps(result, indent=2))
    finally:
        client.close()


if __name__ == '__main__':
    asyncio.run(main())
