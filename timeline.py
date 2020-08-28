from bs4 import BeautifulSoup
import requests
import re
import datetime
from Base import *

def body_text(soup):
    """Returns a string of the Wikipedia Page's body text"""
    ###mw-parser-output contains everything in the actual wikipedia article
    body = soup.find('div', attrs={'class':'mw-parser-output'})
    text = ''
    ###The text is only contained in paragraphs. Charts and boxes aren't included
    allParagraphs = body.find_all('p')
    for i in allParagraphs:
        text += i.text

    return text

def get_sentences(text):
    """Returns all sentences in the text"""
    firstSentence = re.findall(r'^.*?[.!?] ', text)[0]
    otherSentence = re.findall(SENTENCE_PATTERN, text)
    ###The first two characters are a period and a space
    otherSentence = [i[2:] for i in otherSentence]

    sentence = [firstSentence] + otherSentence
    return sentence


def combine_sentences(sentences):
    """Returns a new list of sentences that combines ones that were cutoff at
the wrong point"""
    newSentences = []
    line = ''
    for i in sentences:
        ###Sometimes sentences get cutoff at abbreviations like U.S
        ###The Regex looks for a period and a space, but abbreviations don't have a space
        if(i.count('.')+i.count('!')+i.count('?') > 1):
            line += i
        else:
            newSentences.append(line+i)
            line = ''

    return newSentences

def lifespan(soup):
    """Returns the birth year and death year of a person (if possible)"""
    infobox = soup.find('table', attrs={'class':'infobox'})
    born, died = None, None
    for i in infobox.find_all('tr'):
        if('born' in i.text.lower() and not(born)):
            born = i
        if('died' in i.text.lower() and not(died)):
            died = i

    dieYear = datetime.date.today().year
    bornYear = dieYear-100
    if(born):
        bornYear = birth_year(born.text)
    if(died):
        dieYear = birth_year(died.text)

    return bornYear, dieYear

def birth_year(text):
    """Finds what year a person was born using a line of text"""
    adMatch, bcMatch = re.findall(AD_PATTERN, text), re.findall(BC_PATTERN, text)
    youngMatch = re.findall(YOUNG_PATTERN, text)
    if(youngMatch):
        ###It takes everything inside the parantheses, then takes the first number
        ###Wikipedia uses YYYY-MM-DD
        year = int(youngMatch[0][1:-1].split('-')[0])
        return year

    line = adMatch[0] if adMatch else bcMatch[0]
    return ad_bc_birthday(line)

def ad_bc_birthday(text):
    """Returns birth years when AD/BC is included in the birthday line.
(It is included for old people)"""
    text = text.split()
    ###Sometimes dates are AD 42, and sometimes they are 42 AD
    try:
        year = int(text[-1])
    except ValueError:
        year = int(text[-2])
    if('BC' in text):
        year *= -1

    return year

def time_sentences(sentences, birthYear, deathYear):
    """Gets all sentences that have a year or month in them. """
    newSentences = []
    for i in sentences:
        yearNum = re.findall(OLD_YEAR_PATTERN, i)
        if(not(yearNum)): yearNum = re.findall(YEAR_PATTERN, i)
        if(re.findall(MONTH_PATTERN, i)):
            newSentences.append(i)
        elif(check_year(birthYear, deathYear, yearNum)):
            newSentences.append(i)

    return newSentences

def check_year(birthYear, deathYear, allYears):
    """Finds out whether a certain year is in the person's lifespan.
allYears is a list of years/numbers in a sentence"""
    year = None
    for i in allYears:
        i = i.split(' ')
        thisYear = int(i[0])
        if('BC' in i): thisYear *= -1
        if(thisYear >= birthYear and thisYear <= deathYear):
            year = thisYear
            break

    return year

def get_day(line):
    month = re.findall(MONTH_PATTERN, line)
    if(not(month)):
        return 0
    ###This finds a month word, then 1 or 2 digits.
    ###So January 15 or November 3, but not January 1757
    matchLine = month[0][1:-1] + r' [0-9]{1,2}[^0-9]'
    day = re.findall(matchLine, line)
    if(not(day)):
        return 0
    day = int(day[0][:-1].split(' ')[1])
    if(day >= 32):
        return 0

    return day

def tag_years(sentences, birthYear, deathYear):
    """Tags each sentence with a date"""
    firstYear = birthYear
    newSentences = []
    for i in sentences:
        year = check_year(birthYear, deathYear, re.findall(YEAR_PATTERN, i))
        month = re.findall(MONTH_PATTERN, i)
        day = 0
        if(month):
            month = datetime.datetime.strptime(month[0][1:-1], '%B').month
            day = get_day(i)

        if(year and month):
            firstYear = year
            newSentences.append([i, [month, day, year]])
        elif(month):
            newSentences.append([i, [month, day, firstYear]])
        elif(year):
            firstYear = year
            newSentences.append([i, [0, day, year]])

    return newSentences

def timeline(term=None, soup=None):
    """Creates a timeline from the Wikipedia Page for term"""
    ###Open website, get and clean body text
    if(term == None and soup == None):
        return None
    if(term):
        soup = open_website(term)
    text = body_text(soup)
    text = citations(text)

    ###Get sentences from the wbesite
    allSentences = get_sentences(text)
    newSentences = combine_sentences(allSentences)

    ###Get relevant websites
    birthYear, deathYear = lifespan(soup)
    newSentences = time_sentences(newSentences, birthYear, deathYear)
    newSentences = tag_years(newSentences, birthYear, deathYear)[1:]
    ###Create a timeline
    newSentences = sorted(newSentences, key=lambda x:[x[1][2], x[1][0], x[1][1]])
    return newSentences

def combine_timelines(lines, names):
    """Combines two timelines and sorts them by date"""
    for i in range(len(lines)):
        newLine = lines[i].copy()
        newLine = [[j[0], names[i], j[1]] for j in newLine]
        lines[i] = newLine.copy()

    newLine = []
    for i in lines:
        newLine += i

    return sorted(newLine, key=lambda x:[x[2]])
