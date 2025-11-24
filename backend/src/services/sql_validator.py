"""
SQL Validation Service for Data Agent V4 Backend
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum

from ..models.rag_sql import (
    SQLQuery,
    SQLValidationResult,
    DatabaseSchema,
    QueryType,
)

logger = logging.getLogger(__name__)


class ValidationRiskLevel(Enum):
    """Validation risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SQLValidator:
    """Service for validating SQL queries for security and correctness"""

    def __init__(self):
        # Dangerous SQL keywords that are not allowed
        self.dangerous_keywords = {
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXECUTE', 'EXEC', 'GRANT', 'REVOKE', 'UNION',
            'MERGE', 'CALL', 'DO', 'COPY', 'VACUUM', 'ANALYZE',
            'REINDEX', 'CLUSTER', 'COMMENT', 'SECURITY LABEL'
        }

        # SQL injection patterns
        self.injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bAND\b\s+\d+\s*=\s*\d+)",
            r"(\'\s*;\s*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b)",
            r"(\"\s*;\s*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b)",
            r"(\bUNION\b\s+\bSELECT\b)",
            r"(\bINTO\s+\bOUTFILE\b|\bINTO\s+\bDUMPFILE\b)",
            r"(\bLOAD_FILE\s*\()",
            r"(\bBENCHMARK\s*\()",
            r"(\bSLEEP\s*\()",
            r"(\bWAITFOR\s+\bDELAY\b)",
            r"(\bXP_CMDSHELL\b)"
        ]

        # Query complexity indicators
        self.complexity_indicators = {
            'subqueries': r'\b\(\s*SELECT\b',
            'nested_joins': r'\bJOIN\s+.*\bJOIN\b',
            'multiple_unions': r'(\bUNION\b.*){2,}',
            'recursive_cte': r'\bWITH\s+RECURSIVE\b',
            'window_functions': r'\bOVER\s*\(',
            'complex_aggregations': r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\(\s*.*\bDISTINCT\b'
        }

        # Performance risk patterns
        self.performance_risks = {
            'select_star': r'\bSELECT\s+\*\b',
            'missing_where': r'\bSELECT\b.*\bFROM\b.+(?!\bWHERE\b).*\b(?:ORDER\s+BY|GROUP\s+BY|LIMIT|$)',
            'like_leading_wildcard': r'\bLIKE\s+\'%.*?\'',
            'large_limit': r'\bLIMIT\s+\s*[1-9]\d{3,}',  # LIMIT > 999
            'cross_join': r'\bCROSS\s+JOIN\b',
            'full_outer_join': r'\bFULL\s+OUTER\s+JOIN\b'
        }

    async def validate_sql(
        self,
        sql_query: SQLQuery,
        schema: DatabaseSchema,
        tenant_id: str
    ) -> SQLValidationResult:
        """
        Validate SQL query for security, syntax, and performance

        Args:
            sql_query: SQL query to validate
            schema: Database schema
            tenant_id: Tenant ID for context

        Returns:
            SQLValidationResult: Validation result
        """
        try:
            validation_errors = []
            security_warnings = []
            suggestions = []

            # Check for dangerous keywords
            keyword_errors = self._check_dangerous_keywords(sql_query.query)
            validation_errors.extend(keyword_errors)

            # Check for SQL injection patterns
            injection_errors = self._check_sql_injection(sql_query.query)
            validation_errors.extend(injection_errors)

            # Check table and column access
            access_errors = self._check_table_column_access(sql_query.query, schema, tenant_id)
            validation_errors.extend(access_errors)

            # Check query complexity
            complexity_warnings = self._check_query_complexity(sql_query.query)
            security_warnings.extend(complexity_warnings)

            # Check performance risks
            performance_warnings = self._check_performance_risks(sql_query.query)
            security_warnings.extend(performance_warnings)

            # Generate optimization suggestions
            optimization_suggestions = self._generate_suggestions(sql_query.query, schema)
            suggestions.extend(optimization_suggestions)

            # Calculate risk level
            risk_level = self._calculate_risk_level(validation_errors, security_warnings)

            # Determine overall validity
            is_valid = len(validation_errors) == 0 and risk_level != ValidationRiskLevel.CRITICAL.value

            return SQLValidationResult(
                is_valid=is_valid,
                validation_errors=validation_errors,
                security_warnings=security_warnings,
                risk_level=risk_level,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"Error validating SQL: {str(e)}")
            return SQLValidationResult(
                is_valid=False,
                validation_errors=[f"Validation error: {str(e)}"],
                security_warnings=[],
                risk_level=ValidationRiskLevel.HIGH.value,
                suggestions=["Check SQL syntax and structure"]
            )

    def _check_dangerous_keywords(self, query: str) -> List[str]:
        """Check for dangerous SQL keywords"""
        errors = []
        query_upper = query.upper()

        for keyword in self.dangerous_keywords:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            matches = re.findall(pattern, query_upper, re.IGNORECASE)
            if matches:
                errors.append(f"Dangerous keyword detected: {keyword}")

        return errors

    def _check_sql_injection(self, query: str) -> List[str]:
        """Check for SQL injection patterns"""
        errors = []

        for pattern in self.injection_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if matches:
                errors.append(f"Potential SQL injection pattern detected: {pattern}")

        return errors

    def _check_table_column_access(
        self,
        query: str,
        schema: DatabaseSchema,
        tenant_id: str
    ) -> List[str]:
        """Check if query accesses valid tables and columns for the tenant"""
        errors = []

        # Extract table names from query
        table_names = self._extract_table_names(query)

        # Check if all tables exist in schema
        for table_name in table_names:
            if table_name not in schema.tables:
                errors.append(f"Table '{table_name}' not found in database schema")

        # Extract column names and validate
        column_references = self._extract_column_references(query)
        for column_ref in column_references:
            if '.' in column_ref:
                table_name, column_name = column_ref.split('.', 1)
                if table_name in schema.tables:
                    table_info = schema.tables[table_name]
                    if not any(col.name == column_name for col in table_info.columns):
                        errors.append(f"Column '{column_name}' not found in table '{table_name}'")
            else:
                # Column without table prefix - check if it exists in any referenced table
                found = False
                for table_name in table_names:
                    if table_name in schema.tables:
                        table_info = schema.tables[table_name]
                        if any(col.name == column_ref for col in table_info.columns):
                            found = True
                            break
                if not found:
                    errors.append(f"Column '{column_ref}' not found in any referenced table")

        return errors

    def _check_query_complexity(self, query: str) -> List[str]:
        """Check for query complexity indicators"""
        warnings = []

        for indicator, pattern in self.complexity_indicators.items():
            if re.search(pattern, query, re.IGNORECASE | re.MULTILINE):
                warnings.append(f"Complex query detected: {indicator.replace('_', ' ').title()}")

        # Count JOIN operations
        join_count = len(re.findall(r'\bJOIN\b', query, re.IGNORECASE))
        if join_count > 3:
            warnings.append(f"High number of JOINs detected: {join_count}")

        # Count nested parentheses (indicating subqueries)
        open_parens = query.count('(')
        close_parens = query.count(')')
        if open_parens != close_parens:
            warnings.append("Unbalanced parentheses in query")

        return warnings

    def _check_performance_risks(self, query: str) -> List[str]:
        """Check for performance risk patterns"""
        warnings = []

        for risk, pattern in self.performance_risks.items():
            if re.search(pattern, query, re.IGNORECASE):
                warnings.append(f"Performance risk: {risk.replace('_', ' ').title()}")

        # Check for missing WHERE clause with large tables
        if not re.search(r'\bWHERE\b', query, re.IGNORECASE):
            table_names = self._extract_table_names(query)
            if table_names:
                warnings.append("Query missing WHERE clause - may return all rows")

        return warnings

    def _generate_suggestions(self, query: str, schema: DatabaseSchema) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []

        # Suggest specific columns instead of *
        if re.search(r'\bSELECT\s+\*\b', query, re.IGNORECASE):
            suggestions.append("Consider specifying specific columns instead of using *")

        # Suggest LIMIT clause if missing
        if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
            suggestions.append("Consider adding LIMIT clause to restrict result set size")

        # Suggest WHERE clause if missing
        if not re.search(r'\bWHERE\b', query, re.IGNORECASE):
            suggestions.append("Consider adding WHERE clause to filter results")

        # Suggest indexing hints
        table_names = self._extract_table_names(query)
        for table_name in table_names:
            if table_name in schema.tables:
                table_info = schema.tables[table_name]
                # Check for primary key usage in WHERE clause
                pk_columns = [col.name for col in table_info.columns if col.is_primary_key]
                for pk_col in pk_columns:
                    if pk_col.lower() in query.lower():
                        suggestions.append(f"Good: Using primary key '{pk_col}' for efficient lookup")

        # Suggest ORDER BY optimization
        if re.search(r'\bORDER\s+BY\b', query, re.IGNORECASE):
            if not re.search(r'\bLIMIT\b', query, re.IGNORECASE):
                suggestions.append("Consider adding LIMIT clause to ORDER BY queries")

        return suggestions

    def _calculate_risk_level(
        self,
        validation_errors: List[str],
        security_warnings: List[str]
    ) -> str:
        """Calculate overall risk level"""
        if any("injection" in error.lower() or "dangerous" in error.lower() for error in validation_errors):
            return ValidationRiskLevel.CRITICAL.value
        elif len(validation_errors) > 3:
            return ValidationRiskLevel.HIGH.value
        elif len(validation_errors) > 0 or len(security_warnings) > 5:
            return ValidationRiskLevel.MEDIUM.value
        else:
            return ValidationRiskLevel.LOW.value

    def _extract_table_names(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        table_names = []

        # Find FROM clause tables
        from_match = re.search(r'\bFROM\s+([^;\s]+(?:\s+(?:JOIN|WHERE|GROUP\s+BY|ORDER\s+BY|LIMIT|$)))', query, re.IGNORECASE)
        if from_match:
            from_part = from_match.group(1)
            # Extract table names (simplified)
            tables = re.findall(r'(\w+)', from_part)
            # Filter out SQL keywords
            tables = [t for t in tables if t.upper() not in ['JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'CROSS']]
            table_names.extend(tables)

        # Find JOIN clause tables
        join_matches = re.findall(r'\bJOIN\s+(\w+)', query, re.IGNORECASE)
        table_names.extend(join_matches)

        # Remove duplicates and return
        return list(set(table_names))

    def _extract_column_references(self, query: str) -> List[str]:
        """Extract column references from SQL query"""
        columns = []

        # Extract columns from SELECT clause
        select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM\b', query, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_part = select_match.group(1)
            # Remove function calls and aliases to get column names
            select_part = re.sub(r'\b\w+\s*\([^)]*\)', '', select_part)
            # Extract column names
            column_matches = re.findall(r'(\w+(?:\.\w+)?)', select_part)
            columns.extend(column_matches)

        # Extract columns from WHERE clause
        where_match = re.search(r'\bWHERE\s+(.+?)(?:\s+(?:GROUP\s+BY|ORDER\s+BY|LIMIT|$))', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_part = where_match.group(1)
            column_matches = re.findall(r'(\w+(?:\.\w+)?)', where_part)
            columns.extend(column_matches)

        # Remove SQL keywords and duplicates
        sql_keywords = {'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL'}
        filtered_columns = [col for col in columns if col.upper() not in sql_keywords]

        return list(set(filtered_columns))

    async def validate_query_syntax(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query syntax using EXPLAIN

        Args:
            query: SQL query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # This would typically use a database connection to validate syntax
            # For now, we'll do basic syntax checking
            if not query.strip():
                return False, "Empty query"

            # Check for basic SQL structure
            if not re.search(r'\bSELECT\b', query, re.IGNORECASE):
                return False, "Query must start with SELECT"

            if not re.search(r'\bFROM\b', query, re.IGNORECASE):
                return False, "Query must contain FROM clause"

            # Check for balanced parentheses
            if query.count('(') != query.count(')'):
                return False, "Unbalanced parentheses"

            # Check for balanced quotes
            single_quotes = query.count("'")
            if single_quotes % 2 != 0:
                return False, "Unbalanced single quotes"

            return True, None

        except Exception as e:
            return False, f"Syntax validation error: {str(e)}"

    async def check_query_plan(self, query: str) -> Dict[str, Any]:
        """
        Analyze query execution plan (placeholder for database-specific implementation)

        Args:
            query: SQL query to analyze

        Returns:
            Dict containing query plan analysis
        """
        # This would typically use EXPLAIN ANALYZE on the actual database
        # For now, return a basic analysis based on query structure

        analysis = {
            'estimated_cost': self._estimate_query_cost(query),
            'estimated_rows': self._estimate_result_rows(query),
            'uses_indexes': self._predict_index_usage(query),
            'full_table_scans': self._predict_full_table_scans(query),
            'join_types': self._extract_join_types(query),
            'recommendations': []
        }

        # Generate recommendations based on analysis
        if analysis['estimated_cost'] > 1000:
            analysis['recommendations'].append("High query cost - consider optimization")

        if analysis['full_table_scans'] > 0:
            analysis['recommendations'].append("Full table scan detected - consider adding indexes")

        return analysis

    def _estimate_query_cost(self, query: str) -> float:
        """Estimate query execution cost"""
        base_cost = 10.0

        # Add cost for tables
        table_count = len(self._extract_table_names(query))
        table_cost = table_count * 100.0

        # Add cost for joins
        join_count = len(re.findall(r'\bJOIN\b', query, re.IGNORECASE))
        join_cost = join_count * 500.0

        # Add cost for aggregations
        agg_count = len(re.findall(r'\b(COUNT|SUM|AVG|MAX|MIN)\s*\(', query, re.IGNORECASE))
        agg_cost = agg_count * 200.0

        total_cost = base_cost + table_cost + join_cost + agg_cost
        return total_cost

    def _estimate_result_rows(self, query: str) -> int:
        """Estimate number of rows returned"""
        if re.search(r'\bLIMIT\s+(\d+)', query, re.IGNORECASE):
            limit_match = re.search(r'\bLIMIT\s+(\d+)', query, re.IGNORECASE)
            return int(limit_match.group(1))

        if re.search(r'\bWHERE\b', query, re.IGNORECASE):
            return 1000  # Estimate with WHERE clause
        else:
            return 10000  # Estimate without WHERE clause

    def _predict_index_usage(self, query: str) -> List[str]:
        """Predict which indexes might be used"""
        indexes = []

        # Look for WHERE clause conditions that might use indexes
        if re.search(r'\bWHERE\s+(\w+)\s*=', query, re.IGNORECASE):
            where_match = re.search(r'\bWHERE\s+(\w+)\s*=', query, re.IGNORECASE)
            if where_match:
                column = where_match.group(1)
                indexes.append(f"Potential index on {column}")

        # Look for JOIN conditions that might use indexes
        join_conditions = re.findall(r'(\w+)\s*=\s*(\w+)', query)
        for table_col, ref_col in join_conditions:
            indexes.append(f"Potential index on {table_col}")

        return list(set(indexes))

    def _predict_full_table_scans(self, query: str) -> int:
        """Predict number of full table scans"""
        scans = 0

        # SELECT * without WHERE often results in full table scan
        if re.search(r'\bSELECT\s+\*\b', query, re.IGNORECASE) and not re.search(r'\bWHERE\b', query, re.IGNORECASE):
            scans += 1

        # LIKE with leading wildcard often results in full table scan
        if re.search(r'\bLIKE\s+\'%\'', query, re.IGNORECASE):
            scans += 1

        return scans

    def _extract_join_types(self, query: str) -> List[str]:
        """Extract join types from query"""
        join_types = []

        join_matches = re.findall(r'\b(\w+\s+(?:OUTER\s+)?JOIN)\b', query, re.IGNORECASE)
        for join_type in join_matches:
            join_types.append(join_type.upper())

        return join_types

    async def sanitize_query(self, query: str) -> str:
        """
        Sanitize SQL query to prevent injection

        Args:
            query: SQL query to sanitize

        Returns:
            Sanitized query
        """
        # Remove comments
        sanitized = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)

        # Remove multiple whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Trim whitespace
        sanitized = sanitized.strip()

        return sanitized