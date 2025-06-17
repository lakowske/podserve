"""Performance thresholds and reporting configuration."""

from typing import Dict, Any, List
import json
import time
from pathlib import Path


class PerformanceThresholds:
    """Container performance thresholds and reporting."""
    
    # Default performance thresholds (in seconds)
    DEFAULT_THRESHOLDS = {
        'dns': {
            'container_running': 8.0,
            'health_check_healthy': 15.0,
            'service_responding': 20.0,
            'health_check_execution': 5.0,
            'shutdown_time': 5.0,
            'restart_total_time': 10.0,
            'total_cycle_time': 25.0
        },
        'mail': {
            'container_running': 10.0,
            'health_check_healthy': 30.0,
            'service_responding': 45.0,
            'health_check_execution': 5.0,
            'shutdown_time': 8.0,
            'restart_total_time': 15.0,
            'total_cycle_time': 40.0
        },
        'web': {
            'container_running': 8.0,
            'health_check_healthy': 20.0,
            'service_responding': 25.0,
            'health_check_execution': 3.0,
            'shutdown_time': 6.0,
            'restart_total_time': 12.0,
            'total_cycle_time': 30.0
        },
        'apache': {  # Alias for web
            'container_running': 8.0,
            'health_check_healthy': 20.0,
            'service_responding': 25.0,
            'health_check_execution': 3.0,
            'shutdown_time': 4.0,  # Direct Apache shutdown should be much faster
            'restart_total_time': 8.0,
            'total_cycle_time': 15.0
        }
    }
    
    def __init__(self, results_file: str = "performance_results.json"):
        self.results_file = Path(results_file)
        self.results = []
    
    def get_threshold(self, container_type: str, metric: str) -> float:
        """Get performance threshold for container type and metric."""
        # Determine container type from name
        container_type = container_type.lower()
        for ctype in self.DEFAULT_THRESHOLDS.keys():
            if ctype in container_type:
                return self.DEFAULT_THRESHOLDS[ctype].get(metric, float('inf'))
        
        # Default to strictest threshold if type unknown
        return min(
            thresholds.get(metric, float('inf'))
            for thresholds in self.DEFAULT_THRESHOLDS.values()
        )
    
    def check_threshold(self, container_name: str, metric: str, value: float) -> bool:
        """Check if performance metric meets threshold."""
        threshold = self.get_threshold(container_name, metric)
        return value <= threshold
    
    def record_result(self, container_name: str, test_type: str, results: Dict[str, Any]):
        """Record performance test results."""
        result = {
            'timestamp': time.time(),
            'container_name': container_name,
            'test_type': test_type,
            'results': results,
            'thresholds_met': {}
        }
        
        # Check thresholds for each metric
        for metric, value in results.items():
            if isinstance(value, (int, float)) and metric != 'error':
                threshold = self.get_threshold(container_name, metric)
                result['thresholds_met'][metric] = {
                    'value': value,
                    'threshold': threshold,
                    'passed': value <= threshold
                }
        
        self.results.append(result)
    
    def save_results(self):
        """Save results to JSON file."""
        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def load_results(self) -> List[Dict[str, Any]]:
        """Load previous results from JSON file."""
        if self.results_file.exists():
            with open(self.results_file, 'r') as f:
                return json.load(f)
        return []
    
    def generate_report(self) -> str:
        """Generate performance report."""
        if not self.results:
            return "No performance results available."
        
        report = []
        report.append("CONTAINER PERFORMANCE REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Group results by container
        by_container = {}
        for result in self.results:
            container = result['container_name']
            if container not in by_container:
                by_container[container] = []
            by_container[container].append(result)
        
        for container_name, container_results in by_container.items():
            report.append(f"Container: {container_name}")
            report.append("-" * 40)
            
            latest_result = max(container_results, key=lambda x: x['timestamp'])
            thresholds_met = latest_result.get('thresholds_met', {})
            
            for metric, data in thresholds_met.items():
                value = data['value']
                threshold = data['threshold']
                passed = data['passed']
                status = "✓ PASS" if passed else "✗ FAIL"
                
                report.append(f"  {metric}: {value:.2f}s (threshold: {threshold:.2f}s) {status}")
            
            # Overall status
            all_passed = all(data['passed'] for data in thresholds_met.values())
            overall_status = "✓ ALL THRESHOLDS MET" if all_passed else "✗ SOME THRESHOLDS FAILED"
            report.append(f"  Overall: {overall_status}")
            report.append("")
        
        # Summary statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 30)
        
        total_tests = len(self.results)
        passed_tests = sum(
            1 for result in self.results
            if all(data['passed'] for data in result.get('thresholds_met', {}).values())
        )
        
        report.append(f"Total performance tests: {total_tests}")
        report.append(f"Tests meeting all thresholds: {passed_tests}")
        report.append(f"Success rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "Success rate: N/A")
        
        return "\n".join(report)
    
    def get_optimization_suggestions(self) -> List[str]:
        """Generate optimization suggestions based on results."""
        suggestions = []
        
        if not self.results:
            return ["No performance data available for optimization suggestions."]
        
        # Analyze patterns in failures
        failed_metrics = {}
        for result in self.results:
            container_name = result['container_name']
            for metric, data in result.get('thresholds_met', {}).items():
                if not data['passed']:
                    key = f"{container_name}:{metric}"
                    if key not in failed_metrics:
                        failed_metrics[key] = []
                    failed_metrics[key].append(data['value'] - data['threshold'])
        
        # Generate suggestions
        for failed_key, overages in failed_metrics.items():
            container, metric = failed_key.split(':', 1)
            avg_overage = sum(overages) / len(overages)
            
            if metric == 'container_running':
                suggestions.append(
                    f"Container {container} startup is slow (avg {avg_overage:.2f}s over threshold). "
                    "Consider optimizing Dockerfile, reducing image size, or using healthchecks."
                )
            elif metric == 'health_check_healthy':
                suggestions.append(
                    f"Health checks for {container} are slow (avg {avg_overage:.2f}s over threshold). "
                    "Consider simplifying health check commands or increasing check intervals."
                )
            elif metric == 'service_responding':
                suggestions.append(
                    f"Service response for {container} is slow (avg {avg_overage:.2f}s over threshold). "
                    "Consider optimizing service startup, configuration, or dependencies."
                )
            elif metric == 'health_check_execution':
                suggestions.append(
                    f"Health check execution for {container} is slow (avg {avg_overage:.2f}s over threshold). "
                    "Consider using lighter health check commands or reducing timeout values."
                )
        
        if not suggestions:
            suggestions.append("All containers are meeting performance thresholds! 🎉")
        
        return suggestions


def main():
    """CLI interface for performance threshold management."""
    import sys
    
    thresholds = PerformanceThresholds()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'report':
            # Load and display report
            thresholds.results = thresholds.load_results()
            print(thresholds.generate_report())
        
        elif command == 'suggest':
            # Load and display optimization suggestions
            thresholds.results = thresholds.load_results()
            suggestions = thresholds.get_optimization_suggestions()
            print("OPTIMIZATION SUGGESTIONS")
            print("=" * 40)
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}. {suggestion}")
        
        elif command == 'thresholds':
            # Display current thresholds
            print("CURRENT PERFORMANCE THRESHOLDS")
            print("=" * 50)
            for container_type, metrics in thresholds.DEFAULT_THRESHOLDS.items():
                print(f"\n{container_type.upper()}:")
                for metric, threshold in metrics.items():
                    print(f"  {metric}: {threshold:.1f}s")
        
        else:
            print("Unknown command. Available commands: report, suggest, thresholds")
    
    else:
        print("Usage: python performance_thresholds.py [report|suggest|thresholds]")


if __name__ == "__main__":
    main()