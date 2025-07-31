ANALYSIS_TYPES = {
    "general": "General Business Analysis",
    "competitive": "Competitive Intelligence",
    "customer": "Customer Feedback Analysis"
}
import json

SYSTEM_PROMPTS = {
    "general": """You are a senior business analyst with expertise in analyzing business documents.
Focus on extracting key insights, trends, and actionable recommendations.""",
    
    "competitive": """You are a competitive intelligence expert specializing in market analysis.
Focus on competitor positioning, market threats, opportunities, and strategic implications.""",
    
    "customer": """You are a customer experience analyst specializing in feedback analysis.
Focus on customer sentiment, pain points, satisfaction drivers, and suggested improvements."""
}

ANALYSIS_TEMPLATES = {
    "general": {
        "summary": "Provide a concise executive summary",
        "key_findings": "List the main findings and insights",
        "implications": "Explain business implications",
        "recommendations": "Provide actionable recommendations",
        "content_type": "Classify the document type",
        "quality_score": "Rate document quality 1-10"
    },
    
    "competitive": {
        "summary": "Summarize competitor's current position",
        "market_positioning": "Analyze market positioning and strategy",
        "strengths": "List key competitive strengths",
        "weaknesses": "List key competitive weaknesses",
        "threats": "Identify market threats and challenges",
        "opportunities": "Identify market opportunities",
        "strategic_recommendations": "Provide strategic recommendations"
    },
    
    "customer": {
        "summary": "Summarize overall customer sentiment",
        "satisfaction_score": "Rate customer satisfaction 1-10",
        "positive_points": "List positive feedback points",
        "pain_points": "List customer pain points and concerns",
        "suggested_improvements": "List suggested improvements",
        "priority_actions": "Recommend priority actions",
        "customer_segment": "Identify customer segment if apparent"
    }
}
