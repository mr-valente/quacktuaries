"""Jinja2 template configuration."""

import os
from fastapi.templating import Jinja2Templates

_templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(_templates_dir, exist_ok=True)

templates = Jinja2Templates(directory=_templates_dir)
