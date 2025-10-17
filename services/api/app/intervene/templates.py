"""
Template renderer for incident issue bodies.

Uses simple mustache-style templating for variable substitution.
"""
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional


class TemplateRenderer:
    """Renders markdown templates with variable substitution."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize renderer.
        
        Args:
            template_dir: Directory containing .md templates
                         (defaults to templates/ in same directory)
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self.template_dir = Path(template_dir)
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render template with context variables.
        
        Args:
            template_name: Template filename (with or without .md)
            context: Variables to substitute
            
        Returns:
            Rendered markdown string
        """
        # Load template
        if not template_name.endswith(".md"):
            template_name += ".md"
        
        template_path = self.template_dir / template_name
        if not template_path.exists():
            raise ValueError(f"Template not found: {template_name}")
        
        template = template_path.read_text()
        
        # Render with context
        return self._render_string(template, context)
    
    def _render_string(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render template string with mustache-style variables.
        
        Supports:
        - {{variable}} - Simple substitution
        - {{#section}}...{{/section}} - Conditional sections (if truthy)
        - {{^section}}...{{/section}} - Inverted sections (if falsy)
        """
        # Simple variable substitution: {{variable}}
        def replace_var(match):
            key = match.group(1).strip()
            value = self._get_nested_value(context, key)
            
            # Handle JSON serialization for dicts/lists
            if isinstance(value, (dict, list)):
                return json.dumps(value, indent=2)
            
            return str(value) if value is not None else ""
        
        result = re.sub(r'\{\{([^#^/][^}]*)\}\}', replace_var, template)
        
        # Conditional sections: {{#key}}...{{/key}}
        def replace_section(match):
            key = match.group(1).strip()
            content = match.group(2)
            value = self._get_nested_value(context, key)
            
            # Show section if value is truthy
            if value:
                return self._render_string(content, context)
            return ""
        
        result = re.sub(
            r'\{\{#([^}]+)\}\}(.*?)\{\{/\1\}\}',
            replace_section,
            result,
            flags=re.DOTALL
        )
        
        # Inverted sections: {{^key}}...{{/key}}
        def replace_inverted(match):
            key = match.group(1).strip()
            content = match.group(2)
            value = self._get_nested_value(context, key)
            
            # Show section if value is falsy
            if not value:
                return self._render_string(content, context)
            return ""
        
        result = re.sub(
            r'\{\{\^([^}]+)\}\}(.*?)\{\{/\1\}\}',
            replace_inverted,
            result,
            flags=re.DOTALL
        )
        
        return result
    
    def _get_nested_value(self, context: Dict[str, Any], key: str) -> Any:
        """Get value from nested dict using dot notation."""
        parts = key.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
            
            if value is None:
                return None
        
        return value
    
    def list_templates(self) -> list:
        """List available templates."""
        if not self.template_dir.exists():
            return []
        
        return [
            f.stem for f in self.template_dir.glob("*.md")
        ]


def render_incident_issue(incident: Dict[str, Any]) -> str:
    """
    Render issue body for incident.
    
    Args:
        incident: Incident dict with kind, details, etc.
        
    Returns:
        Rendered markdown issue body
    """
    renderer = TemplateRenderer()
    
    # Map incident kind to template
    template_map = {
        "invariant": "invariant_failure",
        "budget": "budget_exceeded",
        "planner": "planner_regression",
    }
    
    template_name = template_map.get(incident["kind"], "generic_incident")
    
    # Build context from incident
    context = {
        **incident["details"],
        "incident_id": incident["id"],
        "severity": incident["severity"],
        "summary": incident["summary"],
        "status": incident["status"],
        "assigned_to": incident.get("assigned_to"),
        "created_at": incident.get("created_at"),
    }
    
    try:
        return renderer.render(template_name, context)
    except ValueError:
        # Fallback to generic template
        return renderer.render("generic_incident", context)
