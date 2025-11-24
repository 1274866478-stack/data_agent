"""
Query Analysis Service for Data Agent V4 Backend
"""

import re
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta

from ..models.rag_sql import (
    QueryIntent,
    QueryType,
    DatabaseSchema,
    TableInfo,
    ColumnInfo,
)

logger = logging.getLogger(__name__)


class QueryAnalyzer:
    """Service for analyzing natural language queries and extracting intent"""

    def __init__(self):
        # Query type patterns
        self.patterns = {
            QueryType.SELECT: [
                r'\b(show|get|list|display|find|search|look up|retrieve|fetch|what|which|who|where|when)\b',
                r'\b(how many|count|number of)\b',
                r'\b(all|every|each)\b'
            ],
            QueryType.AGGREGATE: [
                r'\b(sum|total|count|average|avg|mean|max|min|total sum|overall)\b',
                r'\b(how many|number of|total count)\b',
                r'\b(per|each|by group|group by)\b'
            ],
            QueryType.JOIN: [
                r'\b(from|with|combined|together|related|associated|linked)\b',
                r'\b(join|merge|combine|union)\b',
                r'\b(between|among|across)\b'
            ],
            QueryType.FILTER: [
                r'\b(where|when|if|that|which|who)\b',
                r'\b(with|having|containing|including)\b',
                r'\b(greater than|less than|equal to|not equal|between|in|not in)\b',
                r'\b(before|after|during|since|until)\b'
            ],
            QueryType.SORT: [
                r'\b(order|sort|rank|top|bottom|first|last|highest|lowest|most|least)\b',
                r'\b(ascending|descending|asc|desc)\b',
                r'\b(limit|show only|first \d+|top \d+)\b'
            ]
        }

        # Entity extraction patterns
        self.time_patterns = [
            r'\b(today|yesterday|tomorrow|now|current)\b',
            r'\b(this week|last week|next week)\b',
            r'\b(this month|last month|next month)\b',
            r'\b(this year|last year|next year)\b',
            r'\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b',
            r'\b(\d{1,2} (days?|weeks?|months?|years?) ago)\b',
            r'\b(in the last \d+ (days?|weeks?|months?|years?))\b'
        ]

        self.comparison_patterns = [
            r'\b(greater than|more than|>)(\s+\d+)?\b',
            r'\b(less than|fewer than|<)(\s+\d+)?\b',
            r'\b(equal to|=|is)(\s+\d+)?\b',
            r'\b(not equal to|!=|not)(\s+\d+)?\b',
            r'\b(between)(\s+\d+\s+and\s+\d+)?\b'
        ]

        self.aggregation_patterns = [
            r'\b(sum|total of|total amount)\b',
            r'\b(count|number of|how many)\b',
            r'\b(average|avg|mean of)\b',
            r'\b(maximum|max|highest)\b',
            r'\b(minimum|min|lowest)\b'
        ]

    async def analyze_query_intent(
        self,
        query: str,
        schema: DatabaseSchema
    ) -> QueryIntent:
        """
        Analyze natural language query and extract intent

        Args:
            query: Natural language query
            schema: Database schema for context

        Returns:
            QueryIntent: Analyzed query intent
        """
        try:
            # Preprocess query
            processed_query = self._preprocess_query(query)

            # Identify query type
            query_type = self._identify_query_type(processed_query)

            # Extract target tables
            target_tables = self._extract_target_tables(processed_query, schema)

            # Extract target columns
            target_columns = self._extract_target_columns(processed_query, schema, target_tables)

            # Extract conditions
            conditions = self._extract_conditions(processed_query)

            # Extract aggregations
            aggregations = self._extract_aggregations(processed_query)

            # Extract groupings
            groupings = self._extract_groupings(processed_query, target_columns)

            # Extract orderings
            orderings = self._extract_orderings(processed_query)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                processed_query, query_type, target_tables, target_columns
            )

            return QueryIntent(
                original_query=query,
                query_type=query_type,
                target_tables=target_tables,
                target_columns=target_columns,
                conditions=conditions,
                aggregations=aggregations,
                groupings=groupings,
                orderings=orderings,
                confidence_score=confidence_score
            )

        except Exception as e:
            logger.error(f"Error analyzing query intent: {str(e)}")
            # Return a basic intent object on error
            return QueryIntent(
                original_query=query,
                query_type=QueryType.SELECT,
                target_tables=[],
                target_columns=[],
                confidence_score=0.0
            )

    def _preprocess_query(self, query: str) -> str:
        """Preprocess query for analysis"""
        # Convert to lowercase
        processed = query.lower().strip()

        # Remove extra whitespace
        processed = re.sub(r'\s+', ' ', processed)

        # Remove punctuation that might interfere with pattern matching
        processed = re.sub(r'[!?.,;]+', ' ', processed)

        return processed

    def _identify_query_type(self, query: str) -> QueryType:
        """Identify the primary query type"""
        type_scores = {}

        for query_type, patterns in self.patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query, re.IGNORECASE))
                score += matches
            type_scores[query_type] = score

        # Find the type with highest score
        max_score = max(type_scores.values())
        if max_score == 0:
            return QueryType.SELECT  # Default type

        # Get all types with max score (handle ties)
        best_types = [t for t, s in type_scores.items() if s == max_score]

        # Prefer aggregation over select when tied
        if QueryType.AGGREGATE in best_types and QueryType.SELECT in best_types:
            return QueryType.AGGREGATE

        # Prefer join over others when tied
        if QueryType.JOIN in best_types:
            return QueryType.JOIN

        return best_types[0]

    def _extract_target_tables(self, query: str, schema: DatabaseSchema) -> List[str]:
        """Extract target tables from query based on schema"""
        found_tables = []
        query_words = set(query.split())

        # Look for exact table name matches
        for table_name in schema.tables.keys():
            table_words = set(table_name.split('_'))
            # Check for exact match or significant word overlap
            if table_name.lower() in query:
                found_tables.append(table_name)
            elif any(word in query_words for word in table_words if len(word) > 2):
                found_tables.append(table_name)

        # If no tables found, try fuzzy matching based on common words
        if not found_tables:
            for table_name, table_info in schema.tables.items():
                # Check if query contains any column names from this table
                for column in table_info.columns:
                    if column.name.lower() in query:
                        found_tables.append(table_name)
                        break

        return list(set(found_tables))  # Remove duplicates

    def _extract_target_columns(
        self,
        query: str,
        schema: DatabaseSchema,
        target_tables: List[str]
    ) -> List[str]:
        """Extract target columns from query"""
        found_columns = []

        # Look for column mentions in query
        query_words = set(query.split())

        for table_name in target_tables:
            if table_name not in schema.tables:
                continue

            table_info = schema.tables[table_name]

            for column in table_info.columns:
                column_words = set(column.name.split('_'))

                # Exact match
                if column.name.lower() in query:
                    found_columns.append(f"{table_name}.{column.name}")
                # Word overlap
                elif any(word in query_words for word in column_words if len(word) > 2):
                    found_columns.append(f"{table_name}.{column.name}")

        # Add commonly requested columns if none found
        if not found_columns and target_tables:
            # Add primary keys and common columns like 'name', 'title', 'id'
            for table_name in target_tables:
                if table_name not in schema.tables:
                    continue

                table_info = schema.tables[table_name]
                common_columns = ['id', 'name', 'title', 'created_at', 'updated_at']

                for column in table_info.columns:
                    if column.name.lower() in common_columns:
                        found_columns.append(f"{table_name}.{column.name}")

        return list(set(found_columns))

    def _extract_conditions(self, query: str) -> List[str]:
        """Extract conditions from query"""
        conditions = []

        # Time-based conditions
        for pattern in self.time_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            conditions.extend(matches)

        # Comparison conditions
        for pattern in self.comparison_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            conditions.extend([match[0] for match in matches])

        # Text-based conditions
        text_patterns = [
            r'\b(containing|includes|with|that|which)\s+(\w+)\b',
            r'\b(starting with|begins with)\s+(\w+)\b',
            r'\b(ending with|ends with)\s+(\w+)\b'
        ]

        for pattern in text_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            conditions.extend([f"{match[0]} {match[1]}" for match in matches])

        return conditions

    def _extract_aggregations(self, query: str) -> List[str]:
        """Extract aggregation functions from query"""
        aggregations = []

        for pattern in self.aggregation_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            aggregations.extend(matches)

        # Normalize aggregation names
        normalized_aggregations = []
        for agg in aggregations:
            agg_lower = agg.lower()
            if agg_lower in ['sum', 'total', 'total amount', 'total of']:
                normalized_aggregations.append('SUM')
            elif agg_lower in ['count', 'number of', 'how many']:
                normalized_aggregations.append('COUNT')
            elif agg_lower in ['average', 'avg', 'mean']:
                normalized_aggregations.append('AVG')
            elif agg_lower in ['max', 'maximum', 'highest']:
                normalized_aggregations.append('MAX')
            elif agg_lower in ['min', 'minimum', 'lowest']:
                normalized_aggregations.append('MIN')
            else:
                normalized_aggregations.append(agg_upper)

        return list(set(normalized_aggregations))

    def _extract_groupings(self, query: str, target_columns: List[str]) -> List[str]:
        """Extract grouping columns from query"""
        groupings = []

        # Look for "group by" patterns
        group_patterns = [
            r'\b(group by|grouped by|per|each|by)\s+(\w+)\b',
            r'\b(for each|by each)\s+(\w+)\b'
        ]

        for pattern in group_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                groupings.append(match[1])

        # Extract from target columns if mentioned with grouping words
        grouping_words = ['per', 'each', 'by', 'for']
        for column in target_columns:
            column_name = column.split('.')[-1]
            for word in grouping_words:
                if f"{word} {column_name}" in query:
                    groupings.append(column_name)

        return list(set(groupings))

    def _extract_orderings(self, query: str) -> List[str]:
        """Extract ordering information from query"""
        orderings = []

        # Sort patterns
        sort_patterns = [
            r'\b(order by|sort by|sorted by)\s+(\w+)\s+(asc|desc|ascending|descending)?\b',
            r'\b(top|bottom|first|last)\s+(\d+)?\s+(\w+)?\b',
            r'\b(highest|lowest|most|least)\s+(\w+)\b'
        ]

        for pattern in sort_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if match[0] in ['highest', 'lowest', 'most', 'least']:
                    direction = 'DESC' if match[0] in ['highest', 'most'] else 'ASC'
                    orderings.append(f"{match[1]} {direction}")
                elif len(match) >= 2:
                    direction = match[1] if match[1] else 'ASC'
                    orderings.append(f"{match[0]} {direction}")

        # Limit patterns
        limit_patterns = [
            r'\b(limit|show only|first|top)\s+(\d+)\b',
            r'\b(\d+)\s+(results?|records?|rows?)\b'
        ]

        for pattern in limit_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                orderings.append(f"LIMIT {match[-1]}")

        return orderings

    def _calculate_confidence_score(
        self,
        query: str,
        query_type: QueryType,
        target_tables: List[str],
        target_columns: List[str]
    ) -> float:
        """Calculate confidence score for the analysis"""
        score = 0.0

        # Base score for successful analysis
        score += 0.3

        # Score for identified query type
        type_patterns = self.patterns.get(query_type, [])
        if type_patterns:
            pattern_matches = sum(len(re.findall(pattern, query, re.IGNORECASE)) for pattern in type_patterns)
            score += min(pattern_matches * 0.1, 0.3)

        # Score for target tables found
        if target_tables:
            score += min(len(target_tables) * 0.1, 0.2)

        # Score for target columns found
        if target_columns:
            score += min(len(target_columns) * 0.05, 0.15)

        # Penalize very short or very long queries
        query_words = len(query.split())
        if query_words < 3 or query_words > 20:
            score -= 0.1

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))

    async def analyze_query_complexity(self, query: str, intent: QueryIntent) -> Dict[str, Any]:
        """
        Analyze query complexity and provide optimization suggestions

        Args:
            query: Original query
            intent: Analyzed query intent

        Returns:
            Dict containing complexity analysis and suggestions
        """
        complexity_score = 0
        factors = []

        # Table count factor
        if len(intent.target_tables) > 1:
            complexity_score += len(intent.target_tables) - 1
            factors.append(f"Multiple tables: {len(intent.target_tables)}")

        # Column count factor
        if len(intent.target_columns) > 10:
            complexity_score += 1
            factors.append(f"Many columns: {len(intent.target_columns)}")

        # Aggregation factor
        if intent.aggregations:
            complexity_score += len(intent.aggregations)
            factors.append(f"Aggregations: {', '.join(intent.aggregations)}")

        # Condition factor
        if intent.conditions:
            complexity_score += len(intent.conditions)
            factors.append(f"Conditions: {len(intent.conditions)}")

        # Grouping factor
        if intent.groupings:
            complexity_score += len(intent.groupings)
            factors.append(f"Groupings: {', '.join(intent.groupings)}")

        # Determine complexity level
        if complexity_score <= 2:
            complexity_level = "LOW"
        elif complexity_score <= 5:
            complexity_level = "MEDIUM"
        else:
            complexity_level = "HIGH"

        # Generate suggestions
        suggestions = []
        if complexity_level == "HIGH":
            suggestions.append("Consider breaking this into multiple simpler queries")
            suggestions.append("Ensure proper indexing on joined columns")
        if len(intent.target_tables) > 3:
            suggestions.append("Consider if all tables are necessary")
        if not intent.conditions and len(intent.target_tables) > 1:
            suggestions.append("Add filters to limit result set")

        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "factors": factors,
            "suggestions": suggestions,
            "estimated_execution_time": self._estimate_execution_time(complexity_score)
        }

    def _estimate_execution_time(self, complexity_score: int) -> str:
        """Estimate query execution time based on complexity"""
        if complexity_score <= 2:
            return "< 1 second"
        elif complexity_score <= 5:
            return "1-3 seconds"
        elif complexity_score <= 8:
            return "3-10 seconds"
        else:
            return "> 10 seconds"