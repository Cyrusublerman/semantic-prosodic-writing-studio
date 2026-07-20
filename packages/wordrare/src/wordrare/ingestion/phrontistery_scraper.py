"""
Phrontistery scraper for rare word collection.

Scrapes words from the Phrontistery International House of Logorrhea.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import logging
from tqdm import tqdm

from ..config import PHRONTISTERY_URL
from ..database import RareLexicon, get_session

logger = logging.getLogger(__name__)


class PhrontisteryScraper:
    """Scrapes rare words from Phrontistery website."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or PHRONTISTERY_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (WordRare Poetry Generator; Educational/Research)'
        })

    def scrape_word_list(self, list_id: str, list_url: str) -> List[Dict[str, str]]:
        """
        Scrape a single word list page.

        Args:
            list_id: Identifier for the list (e.g., "general_a-b")
            list_url: URL of the list page

        Returns:
            List of word dictionaries
        """
        try:
            response = self.session.get(list_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {list_url}: {e}")
            return []

        soup = BeautifulSoup(response.content, 'lxml')
        words = []

        # Phrontistery uses various formats - try to parse definition lists
        # Format: <dt>word</dt><dd>definition</dd>
        for dt in soup.find_all('dt'):
            dd = dt.find_next_sibling('dd')
            if dd:
                word = dt.get_text(strip=True)
                definition = dd.get_text(strip=True)

                words.append({
                    'lemma': word.lower(),
                    'phrontistery_definition': definition,
                    'source_url': list_url,
                    'phrontistery_list_id': list_id
                })

        # Also try table format if no definition lists found
        if not words:
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    word = cells[0].get_text(strip=True)
                    definition = cells[1].get_text(strip=True)

                    if word and definition:
                        words.append({
                            'lemma': word.lower(),
                            'phrontistery_definition': definition,
                            'source_url': list_url,
                            'phrontistery_list_id': list_id
                        })

        logger.info(f"Scraped {len(words)} words from {list_id}")
        return words

    def scrape_all_lists(self, delay: float = 1.0) -> List[Dict[str, str]]:
        """
        Scrape all available word lists.

        Args:
            delay: Delay between requests in seconds (be respectful!)

        Returns:
            Combined list of all words
        """
        # Common Phrontistery word list pages
        # Note: These are example URLs - you should verify actual Phrontistery structure
        word_lists = [
            ("general_a-b", f"{self.base_url}ila2g.html"),
            ("general_c-d", f"{self.base_url}ilc2g.html"),
            ("general_e-f", f"{self.base_url}ile2g.html"),
            ("general_g-h", f"{self.base_url}ilg2g.html"),
            ("general_i-j", f"{self.base_url}ili2g.html"),
            ("general_k-l", f"{self.base_url}ilk2g.html"),
            ("general_m-n", f"{self.base_url}ilm2g.html"),
            ("general_o-p", f"{self.base_url}ilo2g.html"),
            ("general_q-r", f"{self.base_url}ilq2g.html"),
            ("general_s-t", f"{self.base_url}ils2g.html"),
            ("general_u-v", f"{self.base_url}ilu2g.html"),
            ("general_w-z", f"{self.base_url}ilw2g.html"),
            # Add more specialized lists as needed
        ]

        all_words = []

        for list_id, url in tqdm(word_lists, desc="Scraping Phrontistery"):
            words = self.scrape_word_list(list_id, url)
            all_words.extend(words)
            time.sleep(delay)  # Be respectful to the server

        logger.info(f"Total words scraped: {len(all_words)}")
        return all_words

    def save_to_database(self, words: List[Dict[str, str]]):
        """
        Save scraped words to database.

        Args:
            words: List of word dictionaries
        """
        with get_session() as session:
            added = 0
            skipped = 0

            for word_data in tqdm(words, desc="Saving to database"):
                # Check if word already exists
                existing = session.query(RareLexicon).filter_by(
                    lemma=word_data['lemma']
                ).first()

                if existing:
                    skipped += 1
                    continue

                rare_word = RareLexicon(**word_data)
                session.add(rare_word)
                added += 1

                # Commit in batches
                if added % 100 == 0:
                    session.commit()

            session.commit()

        logger.info(f"Added {added} new words, skipped {skipped} existing words")

    def run(self, delay: float = 1.0):
        """
        Run the complete scraping pipeline.

        Args:
            delay: Delay between requests in seconds
        """
        logger.info("Starting Phrontistery scraping...")
        words = self.scrape_all_lists(delay=delay)

        if words:
            logger.info("Saving words to database...")
            self.save_to_database(words)
            logger.info("Scraping complete!")
        else:
            logger.warning("No words were scraped")


def main():
    """Command-line interface for the scraper."""
    logging.basicConfig(level=logging.INFO)
    scraper = PhrontisteryScraper()
    scraper.run()


if __name__ == "__main__":
    main()
