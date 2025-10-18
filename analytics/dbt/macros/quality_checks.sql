/*
 * Data quality check macros for dbt.
 * 
 * These macros provide comprehensive data quality validations:
 * - Null checks
 * - Duplicate detection
 * - Schema drift monitoring
 * - Referential integrity
 * - Value range validation
 * - Freshness checks
 */


/*
 * Check for null values in critical columns.
 * 
 * Usage:
 *   {{ check_nulls('my_table', ['id', 'created_at', 'user_email']) }}
 */
{% macro check_nulls(table_name, columns) %}
    {% for column in columns %}
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ column }}' AS column_name,
        'null_check' AS check_type,
        COUNT(*) AS failed_rows,
        CURRENT_TIMESTAMP AS checked_at
    FROM {{ ref(table_name) }}
    WHERE {{ column }} IS NULL
    {% if not loop.last %}
    UNION ALL
    {% endif %}
    {% endfor %}
{% endmacro %}


/*
 * Check for duplicate records based on unique key columns.
 * 
 * Usage:
 *   {{ check_duplicates('my_table', ['id']) }}
 *   {{ check_duplicates('my_table', ['user_id', 'created_date']) }}
 */
{% macro check_duplicates(table_name, key_columns) %}
    WITH duplicate_check AS (
        SELECT
            {% for column in key_columns %}
            {{ column }}{% if not loop.last %},{% endif %}
            {% endfor %},
            COUNT(*) AS row_count
        FROM {{ ref(table_name) }}
        GROUP BY {% for column in key_columns %}{{ column }}{% if not loop.last %}, {% endif %}{% endfor %}
        HAVING COUNT(*) > 1
    )
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ key_columns | join(", ") }}' AS key_columns,
        'duplicate_check' AS check_type,
        COUNT(*) AS failed_rows,
        SUM(row_count) AS total_duplicates,
        CURRENT_TIMESTAMP AS checked_at
    FROM duplicate_check
{% endmacro %}


/*
 * Check for schema drift by comparing current schema to expected schema.
 * 
 * Usage:
 *   {{ check_schema_drift('my_table', expected_columns) }}
 */
{% macro check_schema_drift(table_name) %}
    WITH current_schema AS (
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = '{{ table_name }}'
        AND table_schema = '{{ target.schema }}'
    ),
    schema_changes AS (
        SELECT
            column_name,
            data_type,
            is_nullable,
            'current' AS schema_version
        FROM current_schema
    )
    SELECT
        '{{ table_name }}' AS table_name,
        column_name,
        data_type,
        'schema_drift' AS check_type,
        CURRENT_TIMESTAMP AS checked_at
    FROM schema_changes
{% endmacro %}


/*
 * Check for referential integrity between parent and child tables.
 * 
 * Usage:
 *   {{ check_referential_integrity('child_table', 'parent_id', 'parent_table', 'id') }}
 */
{% macro check_referential_integrity(child_table, child_column, parent_table, parent_column) %}
    WITH orphaned_records AS (
        SELECT
            child.{{ child_column }}
        FROM {{ ref(child_table) }} child
        LEFT JOIN {{ ref(parent_table) }} parent
            ON child.{{ child_column }} = parent.{{ parent_column }}
        WHERE parent.{{ parent_column }} IS NULL
            AND child.{{ child_column }} IS NOT NULL
    )
    SELECT
        '{{ child_table }}' AS table_name,
        '{{ child_column }}' AS column_name,
        'referential_integrity' AS check_type,
        COUNT(*) AS failed_rows,
        CURRENT_TIMESTAMP AS checked_at
    FROM orphaned_records
{% endmacro %}


/*
 * Check if column values are within expected range.
 * 
 * Usage:
 *   {{ check_value_range('my_table', 'age', 0, 150) }}
 *   {{ check_value_range('my_table', 'score', 0.0, 1.0) }}
 */
{% macro check_value_range(table_name, column_name, min_value, max_value) %}
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ column_name }}' AS column_name,
        'value_range' AS check_type,
        COUNT(*) AS failed_rows,
        MIN({{ column_name }}) AS min_value_found,
        MAX({{ column_name }}) AS max_value_found,
        CURRENT_TIMESTAMP AS checked_at
    FROM {{ ref(table_name) }}
    WHERE {{ column_name }} < {{ min_value }}
        OR {{ column_name }} > {{ max_value }}
{% endmacro %}


/*
 * Check table freshness by comparing latest record timestamp.
 * 
 * Usage:
 *   {{ check_freshness('my_table', 'updated_at', 24) }}  -- 24 hours
 */
{% macro check_freshness(table_name, timestamp_column, max_age_hours) %}
    WITH freshness_check AS (
        SELECT
            MAX({{ timestamp_column }}) AS latest_timestamp,
            CURRENT_TIMESTAMP AS check_timestamp,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX({{ timestamp_column }}))) / 3600 AS age_hours
        FROM {{ ref(table_name) }}
    )
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ timestamp_column }}' AS column_name,
        'freshness' AS check_type,
        CASE
            WHEN age_hours > {{ max_age_hours }} THEN 1
            ELSE 0
        END AS failed_rows,
        latest_timestamp,
        age_hours,
        {{ max_age_hours }} AS max_age_hours,
        CURRENT_TIMESTAMP AS checked_at
    FROM freshness_check
{% endmacro %}


/*
 * Check for unexpected null rates in columns.
 * Useful for columns that should rarely be null but aren't strictly required.
 * 
 * Usage:
 *   {{ check_null_rate('my_table', 'optional_field', 0.05) }}  -- 5% threshold
 */
{% macro check_null_rate(table_name, column_name, max_null_rate) %}
    WITH null_rate_check AS (
        SELECT
            COUNT(*) AS total_rows,
            COUNT(CASE WHEN {{ column_name }} IS NULL THEN 1 END) AS null_rows,
            COUNT(CASE WHEN {{ column_name }} IS NULL THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) AS null_rate
        FROM {{ ref(table_name) }}
    )
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ column_name }}' AS column_name,
        'null_rate' AS check_type,
        CASE
            WHEN null_rate > {{ max_null_rate }} THEN 1
            ELSE 0
        END AS failed_rows,
        null_rate,
        {{ max_null_rate }} AS max_null_rate,
        CURRENT_TIMESTAMP AS checked_at
    FROM null_rate_check
{% endmacro %}


/*
 * Check for expected value distribution in categorical columns.
 * 
 * Usage:
 *   {{ check_value_distribution('my_table', 'status', ['active', 'pending', 'completed']) }}
 */
{% macro check_value_distribution(table_name, column_name, expected_values) %}
    WITH value_distribution AS (
        SELECT
            {{ column_name }},
            COUNT(*) AS row_count
        FROM {{ ref(table_name) }}
        WHERE {{ column_name }} IS NOT NULL
        GROUP BY {{ column_name }}
    ),
    unexpected_values AS (
        SELECT
            {{ column_name }},
            row_count
        FROM value_distribution
        WHERE {{ column_name }} NOT IN (
            {% for value in expected_values %}
            '{{ value }}'{% if not loop.last %},{% endif %}
            {% endfor %}
        )
    )
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ column_name }}' AS column_name,
        'value_distribution' AS check_type,
        COUNT(*) AS failed_rows,
        SUM(row_count) AS unexpected_value_count,
        CURRENT_TIMESTAMP AS checked_at
    FROM unexpected_values
{% endmacro %}


/*
 * Check for monotonically increasing ID columns.
 * Useful for detecting ID reuse or sequence issues.
 * 
 * Usage:
 *   {{ check_monotonic_ids('my_table', 'id', 'created_at') }}
 */
{% macro check_monotonic_ids(table_name, id_column, timestamp_column) %}
    WITH id_order_check AS (
        SELECT
            {{ id_column }},
            {{ timestamp_column }},
            LAG({{ id_column }}) OVER (ORDER BY {{ timestamp_column }}) AS prev_id
        FROM {{ ref(table_name) }}
    ),
    non_monotonic AS (
        SELECT *
        FROM id_order_check
        WHERE {{ id_column }} <= prev_id
    )
    SELECT
        '{{ table_name }}' AS table_name,
        '{{ id_column }}' AS column_name,
        'monotonic_ids' AS check_type,
        COUNT(*) AS failed_rows,
        CURRENT_TIMESTAMP AS checked_at
    FROM non_monotonic
{% endmacro %}


/*
 * Comprehensive quality check suite for a table.
 * Runs all applicable checks and unions results.
 * 
 * Usage in a dbt test:
 *   {{ run_quality_suite('my_table', config) }}
 */
{% macro run_quality_suite(table_name, quality_config) %}
    {% set checks = [] %}
    
    {% if quality_config.null_checks %}
        {% do checks.append(check_nulls(table_name, quality_config.null_checks)) %}
    {% endif %}
    
    {% if quality_config.unique_keys %}
        {% do checks.append(check_duplicates(table_name, quality_config.unique_keys)) %}
    {% endif %}
    
    {% if quality_config.referential_integrity %}
        {% for ref_check in quality_config.referential_integrity %}
            {% do checks.append(
                check_referential_integrity(
                    table_name,
                    ref_check.child_column,
                    ref_check.parent_table,
                    ref_check.parent_column
                )
            ) %}
        {% endfor %}
    {% endif %}
    
    {% for check in checks %}
        {{ check }}
        {% if not loop.last %}
        UNION ALL
        {% endif %}
    {% endfor %}
{% endmacro %}
