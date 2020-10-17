import datetime
import requests
from bs4 import BeautifulSoup
import re
import json

WIKI_BASE = "https://en.wikipedia.org/wiki/"
WIKI_SEARCH_BASE = "https://en.wikipedia.org/w/index.php?search="
###This pattern gets all text inside of two brackets. 
CITATION_PATTERN = r'\[.*?\]'
QUOTE_PATTERN = r"""[.!?]['"] """
SENTENCE_PATTERN = r'(?=([.!?] .*?[.!?] |' + QUOTE_PATTERN + '))'
YOUNG_PATTERN = r'\([0-9\-]*?\)'
#AD_PATTERN = r'AD [0-9]{1,2}'
AD_PATTERN = r'[0-9].*?AD [0-9]{1,4}'
BC_PATTERN = r'[0-9].*BCE?'
#BIRTHDAY_PATTERN = r'\(.*?\)'
YEAR_PATTERN = r'[0-9]{1,4}'
OLD_YEAR_PATTERN = r'[0-9]{1,4} ..'
DATE_PATTERN = r'[0-9 ]*[A-Z]'
###This finds any sentences that end with abbreviations, like "D. "
ABBR_PATTERN = r' [A-Za-z]. $'
###This character is used instead of a hyphen for some things in Wikipedia
SPAN_CHAR = chr(8211)
###This character is used as a "circa"
CIRCA_CHAR = "c."
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

REQUEST_HEADER = {":authority": "en.wikipedia.org",
":method": "GET",
":path": "/w/api.php?action=opensearch&format=json&formatversion=2&search=George%20Was&namespace=0&limit=10",
":scheme": "https",
"accept": "application/json, text/javascript, */*; q=0.01",
"accept-encoding": "gzip, deflate, br",
"accept-language": "en-US,en;q=0.9",
"cache-control": "no-cache",
"cookie": "WMF-Last-Access=17-Oct-2020; WMF-Last-Access-Global=17-Oct-2020; GeoIP=US:MD:Rockville:39.08:-77.17:v4; enwikimwuser-sessionId=ef3885ed5a16873d53b9",
"pragma": "no-cache",
"referer": "https://en.wikipedia.org/w/index.php?title=Special:Search&search=georgefaiuds&ns0=1",
"sec-fetch-dest": "empty",
"sec-fetch-mode": "cors",
"sec-fetch-site": "same-origin",
"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36",
"x-requested-with": "XMLHttpRequest"}
SEARCH_URL = "https://en.wikipedia.org/w/api.php?action=opensearch&format=json&formatversion=2&search={}&namespace=0&limit=5"

def open_website(url):
    """Returns a BeautifulSoup object for a Wikipedia Page"""
    #url = WIKI_BASE + capitalize(searchTerm)
    r = requests.get(url)
    text, redirectUrl = r.text, r.url

    return BeautifulSoup(text, "html.parser"), redirectUrl

def get_person(person):
    """Gets the website for a person"""
    url = WIKI_BASE + capitalize(person)
    return open_website(url)[0]

def search_website(searchTerm):
    """Searches wikipedia for the page closest to searchTerm"""
    searchTerm = "%20".join(searchTerm.split())
    newUrl = SEARCH_URL.format(searchTerm)

    connect = requests.get(newUrl, params=REQUEST_HEADER)
    if(not(connect.ok)):
        return None

    response = json.loads(connect.text)
    if(response[3]):
        return open_website(response[3][0])[0]
    return None

def capitalize(searchTerm):
    searchTerm = [i for i in searchTerm.strip().split() if i != ""]
    searchTerm = [i[0].upper() + i[1:].lower() for i in searchTerm]
    return "_".join(searchTerm)

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

def get_image(soup, height):
    """Returns the url to a picture of the person, and the width of that picture, given a height.
Returns none if a picture is not available"""
    box = soup.find('table', attrs={'class':'infobox'})
    if(not(box)): return

    ###All real Wikipedia images link to a website. Other, smaller images don't
    images = [i.find('img') for i in box.find_all('a')]
    images = [i for i in images if i]
    if(not(images)):
        return

    link = "https:" + images[0]['src']
    ###Scales the width, using the height as a fixed constant
    width = (height/int(images[0]['height']))*int(images[0]['width'])
    return link, width

