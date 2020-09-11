import datetime
import requests
from bs4 import BeautifulSoup
import re

WIKI_BASE = "https://en.wikipedia.org/wiki/"
###This pattern gets all text inside of two brackets. 
CITATION_PATTERN = r'\[.*?\]'
QUOTE_PATTERN = r"""[.!?]['"] """
SENTENCE_PATTERN = r'(?=([.!?] .*?[.!?] |' + QUOTE_PATTERN + '))'
YOUNG_PATTERN = r'\([0-9\-]*?\)'
AD_PATTERN = r'AD [0-9]{1,2}'
BC_PATTERN = r'[0-9].*BCE?'
#BIRTHDAY_PATTERN = r'\(.*?\)'
YEAR_PATTERN = r'[0-9]{1,4}'
OLD_YEAR_PATTERN = r'[0-9]{1,4} ..'
DATE_PATTERN = r'[0-9 ]*[A-Z]'
###This character is used instead of a hyphen for some things in Wikipedia
SPAN_CHAR = chr(8211)
OLD_SPAN_PATTERN = r'[0-9 ABCDE'+SPAN_CHAR+r']+'

MONTH_PATTERN = r''
for i in range(1, 13):
    monthName = datetime.date(1, i, 1).strftime('%B')
    MONTH_PATTERN += ' {} |'.format(monthName)
MONTH_PATTERN = MONTH_PATTERN[:-1]

betweenPhrase = r'[ ,]+'
monthPhrase = r'[A-Z][a-z]+'
dayPhrase = r'[0-9]{1,2}'
yearPhrase = r'[0-9]{1,4}'

FULL_DATE_PATTERN = monthPhrase + betweenPhrase + dayPhrase + betweenPhrase + yearPhrase
BRITISH_PATTERN = dayPhrase + betweenPhrase + monthPhrase + betweenPhrase + yearPhrase

def open_website(searchTerm):
    """Returns a BeautifulSoup object for a Wikipedia Page"""
    url = WIKI_BASE + "_".join(searchTerm.strip().split())
    r = requests.get(url).text

    return BeautifulSoup(r, "html.parser")

def citations(text):
    """Takes the citations out of the body text"""
    text = text.replace('\n', ' ').replace('\t', ' ').replace('\xa0', ' ').strip()
    allCites = re.findall(CITATION_PATTERN, text)
    for i in allCites:
        text = text.replace(i, '')

    return text

def before(date, bench):
    """Finds if one list date ([MM, DD, YYYY]) is before another"""
    return [date[2], date[0], date[1]] < [bench[2], bench[0], bench[1]]

def after(date, bench):
    return not(before(date, bench))



