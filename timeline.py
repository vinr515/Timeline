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
        if(re.findall(ABBR_PATTERN, i)):
            line += i
        else:
            newSentences.append(line+i)
            line = ''
        #if(i.count('.')+i.count('!')+i.count('?') < 1):
        #    line += i
        #else:
        #    newSentences.append(line+i)
        #    line = ''

    return newSentences

def find_life_tags(soup):
    """Finds the two tags that say when the person was alive"""
    infobox = soup.find('table', attrs={'class':'infobox'})
    born, died = None, None
    thisYear = datetime.date.today().year
    if(not(infobox)):
        return [0, 0, thisYear*-10], thisYear
    
    for i in infobox.find_all('tr'):
        if(not(i.find('th'))): continue
        if('born' in i.find('th').text.lower() and not(born)):
            born = i.find('td')
        if('died' in i.find('th').text.lower() and not(died)):
            died = i.find('td')

    return born, died

def find_initial_dates(born, died):
    """Finds the dates for the lifespan. Does not handle cases where one or both
are missing"""
    dieYear = None
    bornYear = None
    if(born):
        try:
            bornYear = birth_year(get_spaced_text(born).strip())
        except ValueError:
            bornYear = None
    if(died):
        try:
            dieYear = birth_year(get_spaced_text(died).strip())
        except ValueError:
            dieYear = None

    return bornYear, dieYear
    
def lifespan(soup):
    """Returns the birth year and death year of a person (if possible)"""
    born, died = find_life_tags(soup)
    if(type(born) == list):
        return born, died

    thisYear = datetime.date.today().year
    bornYear, diedYear = find_initial_dates(born, died)
    
    if(not(bornYear or diedYear)):
        return [1, 0, thisYear*-10], thisYear
    if(not(diedYear) and bornYear):
        if(bornYear[2]+100 >= thisYear):
            diedYear = thisYear
        else:
            diedYear = [bornYear[0], bornYear[1], bornYear[2]+100]
    elif(not(bornYear) and diedYear):
        bornYear = [diedYear[0], diedYear[1], diedYear[2]-100]
        
    if(not(diedYear) and not(bornYear)):
        todayYear = datetime.date.today().year
        return [1, 0, todayYear*-10], todayYear
    
    if(not(bornYear)):
        bornYear = diedYear-100

    if(not(diedYear)):
        diedYear = datetime.date.today().year

    return bornYear, diedYear

def get_spaced_text(tag):
    """Gets the text from the tag, adding spaces when necessary"""
    text = ""
    for i in tag.children:
        if(str(i) == i):
            text += str(i)
        elif(i.name == 'br'):
            text += ' '
        else:
            text += i.text

    text = citations(text).replace(CIRCA_CHAR, "")
    return remove_double_spaces(text)

def remove_double_spaces(text):
    """Removes two spaces in a row, which happen after replacing characters"""
    count = 0
    while("  " in text):
        text = text.replace("  ", " ")
        count += 1
        if(count > 100):
            break
        
    return text

def birth_year(text):
    """Finds what year a person was born using a line of text"""
    adMatch, bcMatch = re.findall(AD_PATTERN, text), re.findall(BC_PATTERN, text)
    youngMatch = re.findall(YOUNG_PATTERN, text)
    if(youngMatch):
        ###It takes everything inside the parantheses, then takes the first number
        ###Wikipedia uses YYYY-MM-DD
        date = list(map(int, youngMatch[0][1:-1].split('-')))
        date = [date[1], date[2], date[0]]
        return date

    britishMatch, regMatch = re.findall(BRITISH_PATTERN, text), re.findall(FULL_DATE_PATTERN, text)
    fullMatch = None
    if(britishMatch): fullMatch = britishMatch[0]
    elif(regMatch): fullMatch = regMatch[0]

    if(fullMatch and not(adMatch or bcMatch)):
        date = fullMatch.replace(',', '').split(' ')
        ###Sometimes the month comes first (June 15 vs 15 June)
        ###The month is the word, the date is the number
        if(date[1].isnumeric()): month, day = date[0], date[1]
        else: month, day = date[1], date[0]
        
        month = datetime.datetime.strptime(month, "%B").month
        return [month, int(day), int(date[2])]

    if(len(adMatch) == 0 and len(bcMatch) == 0):
        year = find_number(text)
        return [0, 0, year]
    
    line = adMatch[0] if adMatch else bcMatch[0]
    return ad_bc_birthday(line)

def find_number(text):
    """Looks through the text to finds a number, adds negative if necessary.
Used if birth/death day only contains the year"""
    numbers = re.findall(r'[0-9]+', text)
    if(not(numbers)):
        raise ValueError("Date had no numbers")
    if('bc' in text.lower()):
        return -(int(numbers[0]))
    return int(numbers[0])

def ad_bc_birthday(text):
    """Returns birth years when AD/BC is included in the birthday line.
(It is included for old people)"""
    newText = text.split()
    ###Sometimes dates are AD 42, and sometimes they are 42 AD
    if(len(newText) == 4):
        month = newText[1] if newText[0].isnumeric() else newText[0]
        month = datetime.datetime.strptime(month, "%B").month

        day = int(newText[0]) if newText[0].isnumeric() else int(newText[1])
        ###AD goes before the number, BC goes after
        ###This checks both
        if(newText[2].isnumeric()):
            return [month, day, -int(newText[2])]
        elif(newText[3].isnumeric()):
            return [month, day, int(newText[3])]
    
    month, day = 0, 0

    return [month, day, find_number(text)]

def time_sentences(sentences, birthYear, deathYear):
    """Gets all sentences that have a year or month in them. """
    newSentences = []
    for i in sentences:
        yearNum = re.findall(OLD_YEAR_PATTERN, i)
        if(not(yearNum)): yearNum = re.findall(YEAR_PATTERN, i)
        if(re.findall(MONTH_PATTERN, i)):
            newSentences.append(i)
        elif(check_year(birthYear, deathYear, i)):
            newSentences.append(i)

    return newSentences

def check_year(birthYear, deathYear, string):
    """Finds out whether a certain year is in the person's lifespan.
allYears is a list of years/numbers in a sentence"""
    allYears = re.findall(OLD_YEAR_PATTERN, string)
    if(not(allYears)):
        allYears = re.findall(YEAR_PATTERN, string)
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
        year = check_year(birthYear, deathYear, i)
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
        soup = search_website(term)
    text = body_text(soup)
    text = citations(text)

    ###Get sentences from the wbesite
    allSentences = get_sentences(text)
    newSentences = combine_sentences(allSentences)

    ###Get relevant websites
    birthDate, deathDate = lifespan(soup)
    birthYear = birthDate if type(birthDate) == int else birthDate[2]
    deathYear = deathDate if type(deathDate) == int else deathDate[2]
    newSentences = time_sentences(newSentences, birthYear, deathYear)
    newSentences = tag_years(newSentences, birthYear, deathYear)[1:]
    ###Create a timeline
    newSentences = sorted(newSentences, key=lambda x:[x[1][2], x[1][0], x[1][1]])

    newSentences = [[i[0].strip()] + i[1:] for i in newSentences]
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
