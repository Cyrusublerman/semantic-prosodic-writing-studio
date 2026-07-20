"""
Data ingestion module for scraping and collecting word data.
"""

from .phrontistery_scraper import PhrontisteryScraper
from .dictionary_enricher import DictionaryEnricher

__all__ = ["PhrontisteryScraper", "DictionaryEnricher"]
