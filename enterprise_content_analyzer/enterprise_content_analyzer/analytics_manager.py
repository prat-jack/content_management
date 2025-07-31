import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import sqlite3
import os
from pathlib import Path

class AnalyticsManager:
    """
    Comprehensive analytics manager for enterprise content analysis.
    Handles time-based analysis, ROI calculations, risk aggregation, and PowerBI exports.
    """
    
    def __init__(self, db_path: str = "analytics.db"):
        """Initialize analytics manager with database."""
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for storing analytics data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create analytics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            document_name TEXT,
            document_type TEXT,
            analysis_type TEXT,
            sentiment_score REAL,
            confidence_score REAL,
            risk_level TEXT,
            cost REAL,
            tokens_used INTEGER,
            processing_time REAL,
            key_insights TEXT,
            action_items TEXT,
            business_impact TEXT,
            priority_score INTEGER
        )
        ''')
        
        # Create ROI tracking table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roi_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            documents_processed INTEGER,
            ai_analysis_cost REAL,
            estimated_manual_cost REAL,
            time_saved_hours REAL,
            efficiency_gain REAL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_analysis(self, analysis_data: Dict[str, Any]) -> None:
        """Record an analysis result for future analytics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract and process data
        result = analysis_data.get('result', {})
        structured_data = result.get('structured_data', {})
        raw_data = result.get('raw_data', {})
        metadata = result.get('analysis_metadata', {})
        
        # Calculate priority score based on multiple factors
        priority_score = self._calculate_priority_score(structured_data, raw_data)
        
        # Extract sentiment and confidence
        sentiment_info = structured_data.get('key_insights', {}).get('sentiment_info', {})
        sentiment_score = sentiment_info.get('quality_score') or sentiment_info.get('satisfaction_score')
        confidence = raw_data.get('confidence', sentiment_info.get('confidence', 0.5))
        
        # Determine risk level
        risk_level = self._determine_risk_level(structured_data, raw_data)
        
        cursor.execute('''
        INSERT INTO analysis_history 
        (document_name, document_type, analysis_type, sentiment_score, confidence_score,
         risk_level, cost, tokens_used, processing_time, key_insights, action_items,
         business_impact, priority_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis_data.get('document_name', 'Unknown'),
            analysis_data.get('document_type', 'Unknown'),
            metadata.get('analysis_type', 'general'),
            sentiment_score,
            confidence,
            risk_level,
            metadata.get('api_cost', 0),
            metadata.get('tokens_used', 0),
            analysis_data.get('processing_time', 0),
            json.dumps(structured_data.get('key_insights', {})),
            json.dumps(structured_data.get('action_items', [])),
            json.dumps(raw_data.get('implications', '')),
            priority_score
        ))
        
        conn.commit()
        conn.close()
    
    def _calculate_priority_score(self, structured_data: Dict, raw_data: Dict) -> int:
        """Calculate priority score (1-100) based on analysis results."""
        score = 50  # Base score
        
        # High-priority keywords in insights
        high_priority_keywords = ['urgent', 'critical', 'immediate', 'risk', 'threat', 'opportunity']
        insights_text = json.dumps(structured_data.get('key_insights', {})).lower()
        
        for keyword in high_priority_keywords:
            if keyword in insights_text:
                score += 10
        
        # Action items with high priority
        action_items = structured_data.get('action_items', [])
        high_priority_actions = sum(1 for item in action_items if item.get('priority') == 'High')
        score += high_priority_actions * 5
        
        # Confidence adjustment
        confidence = raw_data.get('confidence', 0.5)
        if isinstance(confidence, (int, float)):
            score += int((confidence - 0.5) * 20)
        
        return max(1, min(100, score))
    
    def _determine_risk_level(self, structured_data: Dict, raw_data: Dict) -> str:
        """Determine risk level based on analysis content."""
        risk_keywords = {
            'high': ['critical', 'severe', 'urgent', 'threat', 'danger', 'loss'],
            'medium': ['moderate', 'concern', 'issue', 'problem', 'challenge'],
            'low': ['minor', 'slight', 'manageable', 'stable']
        }
        
        text_content = json.dumps({**structured_data, **raw_data}).lower()
        
        high_count = sum(1 for word in risk_keywords['high'] if word in text_content)
        medium_count = sum(1 for word in risk_keywords['medium'] if word in text_content)
        
        if high_count >= 2:
            return 'High'
        elif high_count >= 1 or medium_count >= 3:
            return 'Medium'
        else:
            return 'Low'
    
    def get_time_based_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get time-based analysis trends for the specified period."""
        conn = sqlite3.connect(self.db_path)
        
        # Query data from the last N days
        query = '''
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as analysis_count,
            AVG(sentiment_score) as avg_sentiment,
            AVG(confidence_score) as avg_confidence,
            SUM(cost) as daily_cost,
            AVG(priority_score) as avg_priority,
            COUNT(CASE WHEN risk_level = 'High' THEN 1 END) as high_risk_count,
            COUNT(CASE WHEN risk_level = 'Medium' THEN 1 END) as medium_risk_count,
            COUNT(CASE WHEN risk_level = 'Low' THEN 1 END) as low_risk_count
        FROM analysis_history 
        WHERE timestamp >= datetime('now', '-{} days')
        GROUP BY DATE(timestamp)
        ORDER BY date
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Calculate trends
        trends = {
            'daily_analysis_counts': df['analysis_count'].tolist(),
            'sentiment_trend': df['avg_sentiment'].fillna(0).tolist(),
            'confidence_trend': df['avg_confidence'].fillna(0).tolist(),
            'cost_trend': df['daily_cost'].fillna(0).tolist(),
            'priority_trend': df['avg_priority'].fillna(50).tolist(),
            'risk_distribution': {
                'high': df['high_risk_count'].sum(),
                'medium': df['medium_risk_count'].sum(),
                'low': df['low_risk_count'].sum()
            },
            'dates': df['date'].tolist(),
            'total_analyses': df['analysis_count'].sum(),
            'period_days': days
        }
        
        return trends
    
    def calculate_roi_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Calculate comprehensive ROI metrics."""
        conn = sqlite3.connect(self.db_path)
        
        # Get analysis data for ROI calculation
        query = '''
        SELECT 
            COUNT(*) as total_documents,
            SUM(cost) as total_ai_cost,
            SUM(tokens_used) as total_tokens,
            AVG(processing_time) as avg_processing_time
        FROM analysis_history 
        WHERE timestamp >= datetime('now', '-{} days')
        '''.format(days)
        
        result = conn.execute(query).fetchone()
        conn.close()
        
        total_documents = result[0] or 0
        total_ai_cost = result[1] or 0
        total_tokens = result[2] or 0
        avg_processing_time = result[3] or 0
        
        # ROI calculations
        manual_analysis_cost_per_doc = 150  # Estimated cost for manual analysis
        manual_time_per_doc_hours = 4  # Estimated hours for manual analysis
        hourly_rate = 75  # Estimated hourly rate for analyst
        
        estimated_manual_cost = total_documents * manual_analysis_cost_per_doc
        time_saved_hours = total_documents * manual_time_per_doc_hours
        cost_savings = estimated_manual_cost - total_ai_cost
        roi_percentage = ((cost_savings) / total_ai_cost * 100) if total_ai_cost > 0 else 0
        
        efficiency_gain = (manual_time_per_doc_hours * 60 - (avg_processing_time / 60)) / (manual_time_per_doc_hours * 60) * 100
        
        return {
            'total_documents_analyzed': total_documents,
            'total_ai_cost': round(total_ai_cost, 2),
            'estimated_manual_cost': round(estimated_manual_cost, 2),
            'cost_savings': round(cost_savings, 2),
            'roi_percentage': round(roi_percentage, 1),
            'time_saved_hours': round(time_saved_hours, 1),
            'efficiency_gain_percentage': round(efficiency_gain, 1),
            'cost_per_document': round(total_ai_cost / total_documents, 4) if total_documents > 0 else 0,
            'avg_processing_time_minutes': round(avg_processing_time / 60, 2) if avg_processing_time else 0,
            'period_days': days
        }
    
    def get_risk_aggregation(self) -> Dict[str, Any]:
        """Aggregate risk factors across all documents."""
        conn = sqlite3.connect(self.db_path)
        
        # Risk distribution query
        risk_query = '''
        SELECT 
            risk_level,
            COUNT(*) as count,
            AVG(priority_score) as avg_priority,
            SUM(cost) as total_cost
        FROM analysis_history 
        GROUP BY risk_level
        '''
        
        risk_df = pd.read_sql_query(risk_query, conn)
        
        # Risk by analysis type
        risk_by_type_query = '''
        SELECT 
            analysis_type,
            risk_level,
            COUNT(*) as count
        FROM analysis_history 
        GROUP BY analysis_type, risk_level
        '''
        
        risk_by_type_df = pd.read_sql_query(risk_by_type_query, conn)
        
        # Recent high-risk documents
        high_risk_query = '''
        SELECT 
            document_name,
            analysis_type,
            priority_score,
            timestamp,
            key_insights
        FROM analysis_history 
        WHERE risk_level = 'High'
        ORDER BY timestamp DESC
        LIMIT 10
        '''
        
        high_risk_df = pd.read_sql_query(high_risk_query, conn)
        conn.close()
        
        return {
            'risk_distribution': risk_df.to_dict('records'),
            'risk_by_analysis_type': risk_by_type_df.to_dict('records'),
            'recent_high_risk_documents': high_risk_df.to_dict('records'),
            'total_high_risk': len(high_risk_df),
            'risk_summary': {
                'high_risk_percentage': (risk_df[risk_df['risk_level'] == 'High']['count'].sum() / risk_df['count'].sum() * 100) if not risk_df.empty else 0,
                'medium_risk_percentage': (risk_df[risk_df['risk_level'] == 'Medium']['count'].sum() / risk_df['count'].sum() * 100) if not risk_df.empty else 0,
                'low_risk_percentage': (risk_df[risk_df['risk_level'] == 'Low']['count'].sum() / risk_df['count'].sum() * 100) if not risk_df.empty else 0
            }
        }
    
    def get_priority_action_items(self, limit: int = 20) -> Dict[str, Any]:
        """Get priority action items dashboard data."""
        conn = sqlite3.connect(self.db_path)
        
        # High priority items
        query = '''
        SELECT 
            document_name,
            analysis_type,
            priority_score,
            risk_level,
            action_items,
            timestamp,
            cost
        FROM analysis_history 
        WHERE priority_score >= 70
        ORDER BY priority_score DESC, timestamp DESC
        LIMIT ?
        '''
        
        priority_df = pd.read_sql_query(query, conn, params=[limit])
        
        # Action items by category
        category_query = '''
        SELECT 
            analysis_type,
            COUNT(*) as item_count,
            AVG(priority_score) as avg_priority,
            SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count
        FROM analysis_history 
        WHERE priority_score >= 60
        GROUP BY analysis_type
        ORDER BY avg_priority DESC
        '''
        
        category_df = pd.read_sql_query(category_query, conn)
        conn.close()
        
        # Process action items from JSON
        priority_items = []
        for _, row in priority_df.iterrows():
            try:
                action_items = json.loads(row['action_items']) if row['action_items'] else []
                for item in action_items:
                    if isinstance(item, dict) and item.get('priority') in ['High', 'Medium']:
                        priority_items.append({
                            'document': row['document_name'],
                            'analysis_type': row['analysis_type'],
                            'action': item.get('item', ''),
                            'priority': item.get('priority', 'Medium'),
                            'category': item.get('category', 'General'),
                            'risk_level': row['risk_level'],
                            'priority_score': row['priority_score'],
                            'timestamp': row['timestamp']
                        })
            except (json.JSONDecodeError, TypeError):
                continue
        
        return {
            'high_priority_documents': priority_df.to_dict('records'),
            'priority_action_items': priority_items,
            'action_categories': category_df.to_dict('records'),
            'total_priority_items': len(priority_items),
            'avg_priority_score': priority_df['priority_score'].mean() if not priority_df.empty else 0
        }
    
    def get_sentiment_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get sentiment trends over time."""
        conn = sqlite3.connect(self.db_path)
        
        # Daily sentiment trends
        query = '''
        SELECT 
            DATE(timestamp) as date,
            AVG(sentiment_score) as avg_sentiment,
            AVG(confidence_score) as avg_confidence,
            COUNT(*) as analysis_count,
            analysis_type
        FROM analysis_history 
        WHERE timestamp >= datetime('now', '-{} days')
        AND sentiment_score IS NOT NULL
        GROUP BY DATE(timestamp), analysis_type
        ORDER BY date, analysis_type
        '''.format(days)
        
        sentiment_df = pd.read_sql_query(query, conn)
        
        # Overall sentiment distribution
        distribution_query = '''
        SELECT 
            CASE 
                WHEN sentiment_score >= 7 THEN 'Positive'
                WHEN sentiment_score >= 4 THEN 'Neutral'
                ELSE 'Negative'
            END as sentiment_category,
            COUNT(*) as count,
            analysis_type
        FROM analysis_history 
        WHERE sentiment_score IS NOT NULL
        GROUP BY sentiment_category, analysis_type
        '''
        
        distribution_df = pd.read_sql_query(distribution_query, conn)
        conn.close()
        
        return {
            'daily_sentiment_trends': sentiment_df.to_dict('records'),
            'sentiment_distribution': distribution_df.to_dict('records'),
            'overall_sentiment_avg': sentiment_df['avg_sentiment'].mean() if not sentiment_df.empty else 0,
            'confidence_avg': sentiment_df['avg_confidence'].mean() if not sentiment_df.empty else 0,
            'trend_period_days': days
        }
    
    def export_to_powerbi(self, output_path: str = "powerbi_export.json") -> str:
        """Export comprehensive analytics data in PowerBI-ready format."""
        conn = sqlite3.connect(self.db_path)
        
        # Main analytics dataset
        main_query = '''
        SELECT 
            id,
            timestamp,
            document_name,
            document_type,
            analysis_type,
            sentiment_score,
            confidence_score,
            risk_level,
            cost,
            tokens_used,
            processing_time,
            priority_score,
            DATE(timestamp) as analysis_date,
            strftime('%Y-%m', timestamp) as analysis_month,
            strftime('%Y-%W', timestamp) as analysis_week
        FROM analysis_history
        ORDER BY timestamp DESC
        '''
        
        main_df = pd.read_sql_query(main_query, conn)
        
        # Aggregated metrics
        monthly_agg_query = '''
        SELECT 
            strftime('%Y-%m', timestamp) as month,
            COUNT(*) as documents_analyzed,
            SUM(cost) as total_cost,
            AVG(sentiment_score) as avg_sentiment,
            AVG(confidence_score) as avg_confidence,
            AVG(priority_score) as avg_priority,
            SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
            SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count,
            SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_count
        FROM analysis_history
        GROUP BY strftime('%Y-%m', timestamp)
        ORDER BY month
        '''
        
        monthly_df = pd.read_sql_query(monthly_agg_query, conn)
        conn.close()
        
        # ROI metrics
        roi_metrics = self.calculate_roi_metrics(90)  # 3 months
        
        # Prepare PowerBI export structure
        powerbi_export = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_records": len(main_df),
                "date_range": {
                    "start": main_df['timestamp'].min() if not main_df.empty else None,
                    "end": main_df['timestamp'].max() if not main_df.empty else None
                },
                "version": "1.0"
            },
            "datasets": {
                "analysis_details": main_df.to_dict('records'),
                "monthly_aggregates": monthly_df.to_dict('records'),
                "roi_metrics": [roi_metrics],  # As single-row table for PowerBI
                "risk_summary": self.get_risk_aggregation(),
                "priority_actions": self.get_priority_action_items(50)
            },
            "calculated_measures": {
                "total_cost_savings": roi_metrics['cost_savings'],
                "roi_percentage": roi_metrics['roi_percentage'],
                "avg_sentiment_score": main_df['sentiment_score'].mean() if 'sentiment_score' in main_df.columns else 0,
                "high_risk_percentage": (main_df[main_df['risk_level'] == 'High'].shape[0] / len(main_df) * 100) if not main_df.empty else 0,
                "processing_efficiency": roi_metrics['efficiency_gain_percentage']
            }
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(powerbi_export, f, indent=2, default=str)
        
        return output_path
    
    def get_comprehensive_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data in one call for UI rendering."""
        return {
            'time_trends': self.get_time_based_trends(30),
            'roi_metrics': self.calculate_roi_metrics(30),
            'risk_aggregation': self.get_risk_aggregation(),
            'priority_actions': self.get_priority_action_items(15),
            'sentiment_trends': self.get_sentiment_trends(30),
            'dashboard_timestamp': datetime.now().isoformat()
        }