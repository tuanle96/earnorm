"""Analytics module for logging.

This module provides tools for analyzing logs and generating insights:
- Log queries and aggregations
- Statistical analysis
- Trend detection
- Report generation

Examples:
    >>> from earnorm.logging.analytics import LogAnalyzer, LogReporter
    >>> 
    >>> # Analyze logs
    >>> analyzer = LogAnalyzer()
    >>> stats = await analyzer.get_error_trends(days=7)
    >>> 
    >>> # Generate report
    >>> reporter = LogReporter()
    >>> report = await reporter.generate_daily_report()
"""

from earnorm.logging.analytics.queries import LogAnalyzer
from earnorm.logging.analytics.reports import LogReporter

__all__ = ["LogAnalyzer", "LogReporter"]
