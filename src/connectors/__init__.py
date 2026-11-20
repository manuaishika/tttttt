"""Optional keyed news-API connectors (GNews, NewsAPI).

They add discovery and metadata (real publisher URLs, descriptions) on top of the RSS
collector, which keeps working without any credentials. Each connector turns API articles
into the same raw-entry shape `collect.py` writes, plus `api_source` and `url_type`.
"""
from .base import available_connectors, run_connector  # noqa: F401
