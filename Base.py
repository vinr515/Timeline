import datetime
import requests
from bs4 import BeautifulSoup

WIKI_BASE = "https://en.wikipedia.org/wiki/"
###This pattern gets all text inside of two brackets. 
CITATION_PATTERN = r'\[.*?\]'
QUOTE_PATTERN = r"""[.!?]['"] """
SENTENCE_PATTERN = r'(?=([.!?] .*?[.!?] |' + QUOTE_PATTERN + '))'
YOUNG_PATTERN = r'\([0-9\-]*?\)'
AD_PATTERN = r'AD [0-9]{1,2}'
BC_PATTERN = r'[0-9].*BC'
#BIRTHDAY_PATTERN = r'\(.*?\)'
YEAR_PATTERN = r'[0-9]{1,4}'
OLD_YEAR_PATTERN = r'[0-9]{1,4} ..'
DATE_PATTERN = r'[0-9 ]*[A-Z]'
###This character is used instead of a hyphen for some things in Wikipedia
SPAN_CHAR = chr(8211)

MONTH_PATTERN = r''
for i in range(1, 13):
    monthName = datetime.date(1, i, 1).strftime('%B')
    MONTH_PATTERN += ' {} |'.format(monthName)
MONTH_PATTERN = MONTH_PATTERN[:-1]

def open_website(searchTerm):
    """Returns a BeautifulSoup object for a Wikipedia Page"""
    url = WIKI_BASE + "_".join(searchTerm.strip().split())
    r = requests.get(url).text

    return BeautifulSoup(r, "html.parser")
