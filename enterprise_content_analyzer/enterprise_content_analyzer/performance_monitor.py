import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict, deque

@dataclass
class PerformanceMetric:
    """Data class for storing performance metrics."""
    timestamp: str
    operation: str
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    api_cost: Optional[float] = None
    cache_hit: bool = False
    content_length: Optional[int] = None

class PerformanceMonitor:
    """
    Monitors and tracks performance metrics for the content analyzer.
    """
    
    def __init__(self, log_file: str = "performance_log.json", max_memory_entries: int = 1000):
        """
        Initialize the performance monitor.
        
        Args:
            log_file: File to store performance logs
            max_memory_entries: Maximum number of entries to keep in memory
        """
        self.log_file = log_file
        self.max_memory_entries = max_memory_entries
        self.metrics_queue = deque(maxlen=max_memory_entries)
        self.operation_stats = defaultdict(list)
        self.lock = threading.Lock()
        
        # Cost tracking (approximate OpenAI pricing)
        self.token_costs = {
            'gpt-4o': {'input': 0.005 / 1000, 'output': 0.015 / 1000},  # per token
            'gpt-4': {'input': 0.03 / 1000, 'output': 0.06 / 1000},
            'gpt-3.5-turbo': {'input': 0.001 / 1000, 'output': 0.002 / 1000}
        }
    
    def start_operation(self, operation: str) -> 'OperationTimer':
        """
        Start timing an operation.
        
        Args:
            operation: Name of the operation being timed
            
        Returns:
            OperationTimer context manager
        """
        return OperationTimer(self, operation)
    
    def record_metric(self, metric: PerformanceMetric):
        """
        Record a performance metric.
        
        Args:
            metric: PerformanceMetric to record
        """
        with self.lock:
            self.metrics_queue.append(metric)
            self.operation_stats[metric.operation].append(metric)
            
            # Keep operation stats within reasonable limits
            if len(self.operation_stats[metric.operation]) > 100:
                self.operation_stats[metric.operation].pop(0)
        
        # Write to log file
        self._write_to_log(metric)
    
    def get_operation_stats(self, operation: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get statistics for a specific operation.
        
        Args:
            operation: Operation name
            hours: Number of hours to look back
            
        Returns:
            Dictionary with operation statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            relevant_metrics = [
                m for m in self.operation_stats[operation]
                if datetime.fromisoformat(m.timestamp) > cutoff_time
            ]
        
        if not relevant_metrics:
            return {
                'operation': operation,
                'total_calls': 0,
                'success_rate': 0,
                'avg_duration_ms': 0,
                'total_cost': 0,
                'cache_hit_rate': 0
            }
        
        total_calls = len(relevant_metrics)
        successful_calls = sum(1 for m in relevant_metrics if m.success)
        total_duration = sum(m.duration_ms for m in relevant_metrics)
        total_cost = sum(m.api_cost or 0 for m in relevant_metrics)
        cache_hits = sum(1 for m in relevant_metrics if m.cache_hit)
        
        return {
            'operation': operation,
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'success_rate': (successful_calls / total_calls) * 100,
            'avg_duration_ms': total_duration / total_calls,
            'min_duration_ms': min(m.duration_ms for m in relevant_metrics),
            'max_duration_ms': max(m.duration_ms for m in relevant_metrics),
            'total_cost': total_cost,
            'avg_cost_per_call': total_cost / total_calls if total_calls > 0 else 0,
            'cache_hit_rate': (cache_hits / total_calls) * 100,
            'total_tokens': sum(m.tokens_used or 0 for m in relevant_metrics),
            'error_count': total_calls - successful_calls
        }
    
    def get_overall_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get overall system performance statistics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with overall statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            recent_metrics = [
                m for m in self.metrics_queue
                if datetime.fromisoformat(m.timestamp) > cutoff_time
            ]
        
        if not recent_metrics:
            return {'error': 'No metrics available for the specified time period'}
        
        total_calls = len(recent_metrics)
        successful_calls = sum(1 for m in recent_metrics if m.success)
        total_duration = sum(m.duration_ms for m in recent_metrics)
        total_cost = sum(m.api_cost or 0 for m in recent_metrics)
        cache_hits = sum(1 for m in recent_metrics if m.cache_hit)
        
        # Group by operation
        operations = defaultdict(int)
        for metric in recent_metrics:
            operations[metric.operation] += 1
        
        # Error analysis
        errors = defaultdict(int)
        for metric in recent_metrics:
            if not metric.success and metric.error_message:
                errors[metric.error_message] += 1
        
        return {
            'time_period_hours': hours,
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'success_rate': (successful_calls / total_calls) * 100,
            'avg_duration_ms': total_duration / total_calls,
            'total_cost': total_cost,
            'cache_hit_rate': (cache_hits / total_calls) * 100,
            'operations_breakdown': dict(operations),
            'top_errors': dict(list(errors.items())[:5]),
            'cost_per_hour': total_cost,
            'calls_per_hour': total_calls,
            'avg_cost_per_call': total_cost / total_calls if total_calls > 0 else 0
        }
    
    def calculate_api_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost based on token usage.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        if model not in self.token_costs:
            model = 'gpt-4o'  # Default to gpt-4o pricing
        
        costs = self.token_costs[model]
        input_cost = input_tokens * costs['input']
        output_cost = output_tokens * costs['output']
        
        return input_cost + output_cost
    
    def get_cost_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get detailed cost analysis.
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Cost analysis data
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            recent_metrics = [
                m for m in self.metrics_queue
                if datetime.fromisoformat(m.timestamp) > cutoff_time and m.api_cost is not None
            ]
        
        if not recent_metrics:
            return {'error': 'No cost data available'}
        
        total_cost = sum(m.api_cost for m in recent_metrics)
        total_tokens = sum(m.tokens_used or 0 for m in recent_metrics)
        
        # Cost by operation
        cost_by_operation = defaultdict(float)
        calls_by_operation = defaultdict(int)
        
        for metric in recent_metrics:
            cost_by_operation[metric.operation] += metric.api_cost
            calls_by_operation[metric.operation] += 1
        
        # Hourly breakdown
        hourly_costs = defaultdict(float)
        for metric in recent_metrics:
            hour = datetime.fromisoformat(metric.timestamp).strftime('%Y-%m-%d %H:00')
            hourly_costs[hour] += metric.api_cost
        
        return {
            'time_period_hours': hours,
            'total_cost': total_cost,
            'total_tokens': total_tokens,
            'avg_cost_per_token': total_cost / total_tokens if total_tokens > 0 else 0,
            'cost_by_operation': dict(cost_by_operation),
            'calls_by_operation': dict(calls_by_operation),
            'hourly_costs': dict(sorted(hourly_costs.items())),
            'projected_monthly_cost': (total_cost / hours) * 24 * 30 if hours > 0 else 0
        }
    
    def _write_to_log(self, metric: PerformanceMetric):
        """Write metric to log file."""
        try:
            log_entry = asdict(metric)
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass  # Fail silently for logging errors
    
    def export_metrics(self, hours: int = 24, format: str = 'json') -> str:
        """
        Export metrics data.
        
        Args:
            hours: Number of hours to export
            format: Export format ('json' or 'csv')
            
        Returns:
            Exported data as string
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            recent_metrics = [
                m for m in self.metrics_queue
                if datetime.fromisoformat(m.timestamp) > cutoff_time
            ]
        
        if format.lower() == 'json':
            return json.dumps([asdict(m) for m in recent_metrics], indent=2)
        elif format.lower() == 'csv':
            if not recent_metrics:
                return "No data available"
            
            import io
            import csv
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=asdict(recent_metrics[0]).keys())
            writer.writeheader()
            
            for metric in recent_metrics:
                writer.writerow(asdict(metric))
            
            return output.getvalue()
        else:
            raise ValueError("Unsupported format. Use 'json' or 'csv'")

class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: PerformanceMonitor, operation: str):
        self.monitor = monitor
        self.operation = operation
        self.start_time = None
        self.success = True
        self.error_message = None
        self.tokens_used = None
        self.api_cost = None
        self.cache_hit = False
        self.content_length = None
    
    def __enter__(self) -> 'OperationTimer':
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is not None:
            self.success = False
            self.error_message = str(exc_val)
        
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            operation=self.operation,
            duration_ms=duration_ms,
            success=self.success,
            error_message=self.error_message,
            tokens_used=self.tokens_used,
            api_cost=self.api_cost,
            cache_hit=self.cache_hit,
            content_length=self.content_length
        )
        
        self.monitor.record_metric(metric)
    
    def set_tokens(self, input_tokens: int, output_tokens: int, model: str = 'gpt-4o'):
        """Set token usage for cost calculation."""
        self.tokens_used = input_tokens + output_tokens
        self.api_cost = self.monitor.calculate_api_cost(model, input_tokens, output_tokens)
    
    def set_cache_hit(self, is_hit: bool):
        """Mark whether this was a cache hit."""
        self.cache_hit = is_hit
    
    def set_content_length(self, length: int):
        """Set the content length being processed."""
        self.content_length = length