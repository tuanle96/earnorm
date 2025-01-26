"""Log reporter module.

This module provides tools for generating log reports in various formats.
It supports different types of reports like daily summaries, error reports,
and performance reports.

Examples:
    >>> reporter = LogReporter()
    >>> 
    >>> # Generate daily report
    >>> report = await reporter.generate_daily_report()
    >>> 
    >>> # Generate error report
    >>> error_report = await reporter.generate_error_report(days=7)
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from earnorm.logging.analytics.queries import LogAnalyzer
from earnorm.logging.models.log import Log


class LogReporter:
    """Class for generating log reports.

    This class provides methods for:
    - Generating various types of reports
    - Customizing report formats
    - Exporting reports
    """

    def __init__(self) -> None:
        """Initialize the reporter."""
        self.analyzer = LogAnalyzer()

    async def generate_daily_report(
        self, date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate a daily summary report.

        Args:
            date: Date to generate report for (defaults to yesterday)

        Returns:
            Report dictionary with sections:
            - summary: Overall statistics
            - errors: Error trends and details
            - performance: Performance metrics
            - patterns: Common log patterns
        """
        # Set time range
        date = date or (datetime.now(UTC) - timedelta(days=1))
        start_time = datetime(date.year, date.month, date.day, tzinfo=UTC)
        end_time = start_time + timedelta(days=1)

        # Get various metrics
        error_trends = await self.analyzer.get_error_trends(
            days=1, interval="1h", start_time=start_time, end_time=end_time
        )
        performance = await self.analyzer.get_performance_metrics(
            start_time=start_time, end_time=end_time
        )
        patterns = await self.analyzer.get_log_patterns(
            start_time=start_time, end_time=end_time
        )
        service_stats = await self.analyzer.get_service_stats(days=1)

        # Build report
        return {
            "date": start_time.date().isoformat(),
            "summary": {
                "total_logs": sum(s["log_count"] for s in service_stats.values()),
                "total_errors": sum(s["error_count"] for s in service_stats.values()),
                "total_warnings": sum(
                    s["warning_count"] for s in service_stats.values()
                ),
            },
            "errors": {
                "trends": error_trends,
                "by_service": {
                    service: stats["error_count"]
                    for service, stats in service_stats.items()
                },
            },
            "performance": performance,
            "patterns": patterns[:10],  # Top 10 patterns
            "services": service_stats,
        }

    async def generate_error_report(
        self,
        days: int = 7,
        error_types: Optional[List[str]] = None,
        min_occurrences: int = 5,
    ) -> Dict[str, Any]:
        """Generate a detailed error report.

        Args:
            days: Number of days to analyze
            error_types: List of error types to include
            min_occurrences: Minimum occurrences for patterns

        Returns:
            Report dictionary with sections:
            - summary: Error statistics
            - trends: Error trends over time
            - patterns: Common error patterns
            - services: Error rates by service
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Get error data
        trends = await self.analyzer.get_error_trends(
            days=days, interval="1d", error_types=error_types
        )
        patterns = await self.analyzer.get_log_patterns(
            start_time=start_time,
            end_time=end_time,
            min_occurrences=min_occurrences,
            level="ERROR",
        )
        service_stats = await self.analyzer.get_service_stats(days=days)

        # Calculate summary
        total_errors = sum(t["count"] for t in trends)
        avg_daily_errors = total_errors / days if days > 0 else 0

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days,
            },
            "summary": {
                "total_errors": total_errors,
                "avg_daily_errors": avg_daily_errors,
                "error_types": len(set(t["error_type"] for t in trends)),
            },
            "trends": trends,
            "patterns": patterns,
            "services": {
                service: {
                    "error_count": stats["error_count"],
                    "error_rate": (
                        (stats["error_count"] / stats["log_count"] * 100)
                        if stats["log_count"] > 0
                        else 0
                    ),
                }
                for service, stats in service_stats.items()
            },
        }

    async def generate_performance_report(
        self, days: int = 7, services: Optional[List[str]] = None, interval: str = "1h"
    ) -> Dict[str, Any]:
        """Generate a performance analysis report.

        Args:
            days: Number of days to analyze
            services: List of services to include
            interval: Time interval for trends

        Returns:
            Report dictionary with sections:
            - summary: Overall performance metrics
            - trends: Performance trends over time
            - services: Service-level metrics
            - alerts: Performance alerts/issues
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Get performance data
        overall_metrics = await self.analyzer.get_performance_metrics(
            start_time=start_time, end_time=end_time
        )
        service_stats = await self.analyzer.get_service_stats(
            services=services, days=days
        )

        # Get performance trends
        trends = await self._get_performance_trends(
            start_time=start_time,
            end_time=end_time,
            interval=interval,
            services=services,
        )

        # Generate alerts
        alerts = self._generate_performance_alerts(
            trends=trends, service_stats=service_stats
        )

        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "days": days,
            },
            "summary": overall_metrics,
            "trends": trends,
            "services": {
                service: {
                    "avg_response_time": stats["avg_response_time"],
                    "request_count": stats.get("request_count", 0),
                    "error_rate": stats.get("error_rate", 0),
                }
                for service, stats in service_stats.items()
            },
            "alerts": alerts,
        }

    async def _get_performance_trends(
        self,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        services: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get performance trends over time."""
        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                    "type": "request",
                }
            }
        ]

        if services:
            pipeline[0]["$match"]["service"] = {"$in": services}

        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": {
                            "interval": {
                                "$dateTrunc": {
                                    "date": "$timestamp",
                                    "unit": interval[:-1],
                                    "binSize": int(interval[:-1]),
                                }
                            },
                            "service": "$service",
                        },
                        "avg_response_time": {"$avg": "$response_time"},
                        "request_count": {"$sum": 1},
                        "error_count": {
                            "$sum": {"$cond": [{"$eq": ["$level", "ERROR"]}, 1, 0]}
                        },
                    }
                },
                {"$sort": {"_id.interval": 1}},
            ]
        )

        results = await Log.aggregate(pipeline)
        return [
            {
                "time": r["_id"]["interval"],
                "service": r["_id"]["service"],
                "avg_response_time": r["avg_response_time"],
                "request_count": r["request_count"],
                "error_rate": (
                    (r["error_count"] / r["request_count"] * 100)
                    if r["request_count"] > 0
                    else 0
                ),
            }
            for r in results
        ]

    def _generate_performance_alerts(
        self, trends: List[Dict[str, Any]], service_stats: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate performance alerts based on trends."""
        alerts = []

        # Alert thresholds
        RESPONSE_TIME_THRESHOLD = 1000  # ms
        ERROR_RATE_THRESHOLD = 5  # %
        REQUEST_DROP_THRESHOLD = 50  # %

        for service, stats in service_stats.items():
            # Check average response time
            if stats["avg_response_time"] > RESPONSE_TIME_THRESHOLD:
                alerts.append(
                    {
                        "type": "high_response_time",
                        "service": service,
                        "value": stats["avg_response_time"],
                        "threshold": RESPONSE_TIME_THRESHOLD,
                    }
                )

            # Check error rate
            error_rate = stats.get("error_rate", 0)
            if error_rate > ERROR_RATE_THRESHOLD:
                alerts.append(
                    {
                        "type": "high_error_rate",
                        "service": service,
                        "value": error_rate,
                        "threshold": ERROR_RATE_THRESHOLD,
                    }
                )

        # Check for request volume drops
        service_trends = {}
        for trend in trends:
            service = trend["service"]
            if service not in service_trends:
                service_trends[service] = []
            service_trends[service].append(trend)

        for service, service_data in service_trends.items():
            if len(service_data) < 2:
                continue

            # Compare latest with previous interval
            latest = service_data[-1]
            previous = service_data[-2]
            if previous["request_count"] > 0:
                drop_pct = (
                    (previous["request_count"] - latest["request_count"])
                    / previous["request_count"]
                    * 100
                )
                if drop_pct > REQUEST_DROP_THRESHOLD:
                    alerts.append(
                        {
                            "type": "request_volume_drop",
                            "service": service,
                            "value": drop_pct,
                            "threshold": REQUEST_DROP_THRESHOLD,
                            "current": latest["request_count"],
                            "previous": previous["request_count"],
                        }
                    )

        return alerts
