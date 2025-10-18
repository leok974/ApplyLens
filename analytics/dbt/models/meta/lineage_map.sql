/*
 * Data lineage tracking model.
 * 
 * Generates a lineage graph showing:
 * - Source tables and their dependencies
 * - Transformation flows
 * - Impact analysis for schema changes
 */

{{ config(
    materialized='table',
    tags=['meta', 'lineage']
) }}

WITH source_tables AS (
    -- Track all source tables in the warehouse
    SELECT
        'source' AS node_type,
        table_schema || '.' || table_name AS node_id,
        table_name AS node_name,
        table_schema AS schema_name,
        NULL AS parent_id,
        0 AS depth_level,
        CURRENT_TIMESTAMP AS analyzed_at
    FROM information_schema.tables
    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        AND table_type = 'BASE TABLE'
),

dbt_models AS (
    -- Track dbt models and their dependencies
    SELECT
        'dbt_model' AS node_type,
        '{{ target.schema }}.' || model_name AS node_id,
        model_name AS node_name,
        '{{ target.schema }}' AS schema_name,
        NULL AS parent_id,
        1 AS depth_level,
        CURRENT_TIMESTAMP AS analyzed_at
    FROM (
        -- List of all dbt models in this project
        VALUES
            ('inbox_triage_events'),
            ('inbox_search_queries'),
            ('knowledge_graph_nodes'),
            ('warehouse_health_metrics'),
            ('agent_performance_summary')
    ) AS models(model_name)
),

-- Track agent dependencies
agent_dependencies AS (
    SELECT
        'agent' AS node_type,
        'agent.' || agent_name AS node_id,
        agent_name AS node_name,
        'agents' AS schema_name,
        source_model AS parent_id,
        2 AS depth_level,
        CURRENT_TIMESTAMP AS analyzed_at
    FROM (
        VALUES
            ('inbox.triage', '{{ target.schema }}.inbox_triage_events'),
            ('inbox.search', '{{ target.schema }}.inbox_search_queries'),
            ('knowledge.search', '{{ target.schema }}.knowledge_graph_nodes'),
            ('warehouse.health', '{{ target.schema }}.warehouse_health_metrics'),
            ('planner.deploy', '{{ target.schema }}.agent_performance_summary'),
            ('analytics.insights', '{{ target.schema }}.agent_performance_summary')
    ) AS deps(agent_name, source_model)
),

-- Track data flows between tables
data_flows AS (
    SELECT
        source_id AS from_node,
        target_id AS to_node,
        flow_type,
        CURRENT_TIMESTAMP AS created_at
    FROM (
        VALUES
            -- Raw data to dbt models
            ('public.raw_inbox_events', '{{ target.schema }}.inbox_triage_events', 'transformation'),
            ('public.raw_search_logs', '{{ target.schema }}.inbox_search_queries', 'transformation'),
            ('public.raw_knowledge_graph', '{{ target.schema }}.knowledge_graph_nodes', 'transformation'),
            ('public.raw_metrics', '{{ target.schema }}.warehouse_health_metrics', 'transformation'),
            
            -- dbt models to agent dependencies
            ('{{ target.schema }}.inbox_triage_events', 'agent.inbox.triage', 'consumption'),
            ('{{ target.schema }}.inbox_search_queries', 'agent.inbox.search', 'consumption'),
            ('{{ target.schema }}.knowledge_graph_nodes', 'agent.knowledge.search', 'consumption'),
            ('{{ target.schema }}.warehouse_health_metrics', 'agent.warehouse.health', 'consumption'),
            ('{{ target.schema }}.agent_performance_summary', 'agent.planner.deploy', 'consumption'),
            ('{{ target.schema }}.agent_performance_summary', 'agent.analytics.insights', 'consumption')
    ) AS flows(source_id, target_id, flow_type)
),

-- Combine all nodes
all_nodes AS (
    SELECT * FROM source_tables
    UNION ALL
    SELECT * FROM dbt_models
    UNION ALL
    SELECT * FROM agent_dependencies
),

-- Calculate impact metrics
impact_analysis AS (
    SELECT
        n.node_id,
        n.node_name,
        n.node_type,
        COUNT(DISTINCT df.to_node) AS downstream_count,
        COUNT(DISTINCT df.from_node) FILTER (WHERE df.from_node = n.node_id) AS direct_dependents,
        CASE
            WHEN COUNT(DISTINCT df.to_node) > 5 THEN 'high'
            WHEN COUNT(DISTINCT df.to_node) > 2 THEN 'medium'
            ELSE 'low'
        END AS impact_level
    FROM all_nodes n
    LEFT JOIN data_flows df ON n.node_id = df.from_node
    GROUP BY n.node_id, n.node_name, n.node_type
)

-- Final lineage map
SELECT
    n.node_id,
    n.node_name,
    n.node_type,
    n.schema_name,
    n.parent_id,
    n.depth_level,
    ia.downstream_count,
    ia.impact_level,
    df_out.to_node AS downstream_node,
    df_out.flow_type AS downstream_flow_type,
    df_in.from_node AS upstream_node,
    df_in.flow_type AS upstream_flow_type,
    n.analyzed_at
FROM all_nodes n
LEFT JOIN impact_analysis ia ON n.node_id = ia.node_id
LEFT JOIN data_flows df_out ON n.node_id = df_out.from_node
LEFT JOIN data_flows df_in ON n.node_id = df_in.to_node
ORDER BY n.depth_level, n.node_name
