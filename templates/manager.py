import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("cost_aware_llm.templates")

class TemplateManager:
    """
    Manages prompt templates to allow prompt reuse and dynamic variable injection.
    Stores templates in memory (with persistent fallback if configured).
    """
    def __init__(self, templates_dir: str = "configs/templates"):
        self.templates_dir = templates_dir
        self._templates: Dict[str, str] = {}
        self._load_templates()

    def _load_templates(self):
        """Load templates from the file system."""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            return

        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".txt") or filename.endswith(".j2") or filename.endswith(".md"):
                template_id = os.path.splitext(filename)[0]
                filepath = os.path.join(self.templates_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self._templates[template_id] = f.read()
                except Exception as e:
                    logger.error(f"Failed to load template {filename}: {e}")
                    
        logger.info(f"Loaded {len(self._templates)} prompt templates.")

    def add_template(self, template_id: str, content: str) -> None:
        """Register a new template."""
        self._templates[template_id] = content
        
        # Persist to disk
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            
        filepath = os.path.join(self.templates_dir, f"{template_id}.txt")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to save template {template_id} to disk: {e}")

    def render(self, template_id: str, variables: Dict[str, Any]) -> str:
        """Render a template with variables."""
        if template_id not in self._templates:
            raise ValueError(f"Template '{template_id}' not found.")
            
        template_str = self._templates[template_id]
        try:
            return template_str.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing variable {e} for template '{template_id}'")
        except Exception as e:
            raise ValueError(f"Error formatting template '{template_id}': {e}")

# Global manager instance
template_manager = TemplateManager()
