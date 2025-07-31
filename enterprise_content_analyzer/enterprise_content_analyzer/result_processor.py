import json
import re
from typing import Dict, List, Any, Optional

class ResultProcessor:
    def __init__(self):
        self.fallback_patterns = {
            'summary': r'"summary"\s*:\s*"([^"]+)"',
            'key_findings': r'"key_findings"\s*:\s*\[([^\]]+)\]',
            'recommendations': r'"recommendations"\s*:\s*\[([^\]]+)\]',
            'quality_score': r'"quality_score"\s*:\s*([0-9.]+)',
            'confidence': r'"confidence"\s*:\s*([0-9.]+)'
        }

    def process_json_response(self, json_string: str) -> Dict[str, Any]:
        """
        Safely parses a JSON string and processes its content.
        Handles malformed JSON gracefully with multiple fallback strategies.
        """
        # First attempt: Standard JSON parsing
        parsed_data = self._parse_json_primary(json_string)
        
        if parsed_data is None:
            # Second attempt: Clean and retry
            parsed_data = self._parse_json_with_cleaning(json_string)
        
        if parsed_data is None:
            # Third attempt: Regex fallback
            parsed_data = self._parse_with_regex_fallback(json_string)
        
        if parsed_data is None:
            # Final fallback: Error response
            return {
                "success": False,
                "error": "Unable to parse JSON response with any method",
                "raw_response": json_string[:500] + "..." if len(json_string) > 500 else json_string
            }
        
        return {
            "success": True,
            "insights": self._extract_insights(parsed_data),
            "summary": self._generate_executive_summary(parsed_data),
            "action_items": self._create_action_items(parsed_data),
            "structured_data": self._create_structured_insights(parsed_data),
            "raw_data": parsed_data
        }
    
    def _parse_json_primary(self, json_string: str) -> Optional[Dict[str, Any]]:
        """Primary JSON parsing attempt."""
        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            return None
        except Exception:
            return None
    
    def _parse_json_with_cleaning(self, json_string: str) -> Optional[Dict[str, Any]]:
        """Secondary parsing with JSON cleaning."""
        try:
            # Clean common JSON issues
            cleaned = json_string.strip()
            # Remove potential markdown code blocks
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            # Fix trailing commas
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            return json.loads(cleaned)
        except (json.JSONDecodeError, Exception):
            return None
    
    def _parse_with_regex_fallback(self, json_string: str) -> Optional[Dict[str, Any]]:
        """Regex-based fallback parsing for critical fields."""
        try:
            fallback_data = {}
            for field, pattern in self.fallback_patterns.items():
                match = re.search(pattern, json_string, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    if field in ['quality_score', 'confidence']:
                        try:
                            fallback_data[field] = float(value)
                        except ValueError:
                            fallback_data[field] = value
                    else:
                        fallback_data[field] = value
            
            return fallback_data if fallback_data else None
        except Exception:
            return None

    def _extract_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts insights from parsed JSON data based on analysis templates.
        Handles different analysis types (general, competitive, customer).
        """
        insights = {
            'key_points': [],
            'critical_findings': [],
            'sentiment_info': {},
            'risk_assessment': []
        }
        
        # Extract key findings/points
        key_findings = data.get('key_findings', [])
        if isinstance(key_findings, list):
            insights['key_points'] = key_findings
        elif isinstance(key_findings, str):
            insights['key_points'] = [key_findings]
        
        # Extract strengths, weaknesses, opportunities (competitive analysis)
        for field in ['strengths', 'weaknesses', 'opportunities', 'threats']:
            values = data.get(field, [])
            if values:
                if isinstance(values, list):
                    insights['critical_findings'].extend([f"{field.title()}: {v}" for v in values])
                else:
                    insights['critical_findings'].append(f"{field.title()}: {values}")
        
        # Extract positive/negative points (customer analysis)
        positive_points = data.get('positive_points', [])
        pain_points = data.get('pain_points', [])
        if positive_points:
            if isinstance(positive_points, list):
                insights['critical_findings'].extend([f"Positive: {p}" for p in positive_points])
            else:
                insights['critical_findings'].append(f"Positive: {positive_points}")
        if pain_points:
            if isinstance(pain_points, list):
                insights['critical_findings'].extend([f"Pain Point: {p}" for p in pain_points])
            else:
                insights['critical_findings'].append(f"Pain Point: {pain_points}")
        
        # Sentiment analysis info
        insights['sentiment_info'] = {
            'satisfaction_score': data.get('satisfaction_score'),
            'quality_score': data.get('quality_score'),
            'overall_sentiment': data.get('summary', 'N/A')
        }
        
        return insights

    def _generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """
        Generates a comprehensive executive summary from parsed JSON data.
        Combines multiple fields to create a cohesive summary.
        """
        summary_parts = []
        
        # Primary summary
        main_summary = data.get('summary', '')
        if main_summary:
            summary_parts.append(f"**Overview:** {main_summary}")
        
        # Key metrics
        metrics = []
        quality_score = data.get('quality_score')
        satisfaction_score = data.get('satisfaction_score')
        
        if quality_score:
            try:
                score = float(quality_score)
                metrics.append(f"Quality Score: {score}/10")
            except (ValueError, TypeError):
                metrics.append(f"Quality Score: {quality_score}")
        
        if satisfaction_score:
            try:
                score = float(satisfaction_score)
                metrics.append(f"Satisfaction Score: {score}/10")
            except (ValueError, TypeError):
                metrics.append(f"Satisfaction Score: {satisfaction_score}")
        
        if metrics:
            summary_parts.append(f"**Key Metrics:** {', '.join(metrics)}")
        
        # Business implications
        implications = data.get('implications') or data.get('market_positioning') or data.get('strategic_implications')
        if implications:
            summary_parts.append(f"**Business Impact:** {implications}")
        
        # Content classification
        content_type = data.get('content_type')
        customer_segment = data.get('customer_segment')
        if content_type:
            summary_parts.append(f"**Document Type:** {content_type}")
        if customer_segment:
            summary_parts.append(f"**Customer Segment:** {customer_segment}")
        
        return '\n\n'.join(summary_parts) if summary_parts else "No executive summary available."

    def _create_action_items(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Creates structured action items with priorities from analysis results.
        Extracts actions from recommendations, improvements, and strategic actions.
        """
        action_items = []
        
        # Extract from recommendations
        recommendations = data.get('recommendations', [])
        if isinstance(recommendations, list):
            for rec in recommendations:
                if isinstance(rec, dict):
                    action_items.append({
                        'item': rec.get('action', rec.get('item', str(rec))),
                        'priority': rec.get('priority', 'Medium'),
                        'category': 'Recommendation'
                    })
                else:
                    action_items.append({
                        'item': str(rec),
                        'priority': 'Medium',
                        'category': 'Recommendation'
                    })
        elif isinstance(recommendations, str):
            action_items.append({
                'item': recommendations,
                'priority': 'Medium',
                'category': 'Recommendation'
            })
        
        # Extract from strategic recommendations
        strategic_recs = data.get('strategic_recommendations', [])
        if isinstance(strategic_recs, list):
            for rec in strategic_recs:
                action_items.append({
                    'item': str(rec),
                    'priority': 'High',
                    'category': 'Strategic'
                })
        elif isinstance(strategic_recs, str):
            action_items.append({
                'item': strategic_recs,
                'priority': 'High',
                'category': 'Strategic'
            })
        
        # Extract from suggested improvements
        improvements = data.get('suggested_improvements', [])
        if isinstance(improvements, list):
            for imp in improvements:
                action_items.append({
                    'item': str(imp),
                    'priority': 'Medium',
                    'category': 'Improvement'
                })
        elif isinstance(improvements, str):
            action_items.append({
                'item': improvements,
                'priority': 'Medium',
                'category': 'Improvement'
            })
        
        # Extract from priority actions
        priority_actions = data.get('priority_actions', [])
        if isinstance(priority_actions, list):
            for action in priority_actions:
                action_items.append({
                    'item': str(action),
                    'priority': 'High',
                    'category': 'Priority Action'
                })
        elif isinstance(priority_actions, str):
            action_items.append({
                'item': priority_actions,
                'priority': 'High',
                'category': 'Priority Action'
            })
        
        return action_items
    
    def _create_structured_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a structured format of insights for better display.
        """
        structured = {
            'executive_summary': self._generate_executive_summary(data),
            'key_insights': self._extract_insights(data),
            'action_items': self._create_action_items(data),
            'metadata': {
                'quality_score': data.get('quality_score'),
                'satisfaction_score': data.get('satisfaction_score'),
                'content_type': data.get('content_type'),
                'customer_segment': data.get('customer_segment')
            }
        }
        return structured
