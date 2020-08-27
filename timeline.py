from bs4 import BeautifulSoup
import requests
import re
import datetime

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

def citations(text):
    """Takes the citations out of the body text"""
    text = text.replace('\n', ' ').replace('\t', ' ').replace('\xa0', ' ').strip()
    allCites = re.findall(CITATION_PATTERN, text)
    for i in allCites:
        text = text.replace(i, '')

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
        return 1
    ###This finds a month word, then 1 or 2 digits.
    ###So January 15 or November 3, but not January 1757
    matchLine = month[0][1:-1] + r' [0-9]{1,2}[^0-9]'
    day = re.findall(matchLine, line)
    if(not(day)):
        return 1
    day = int(day[0][:-1].split(' ')[1])
    if(day >= 32):
        return 1

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
            newSentences.append([i, [0, day, year]])

    return newSentences

def timeline(term):
    """Creates a timeline from the Wikipedia Page for term"""
    ###Open website, get and clean body text
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
    newSentences = sorted(newSentences, key=lambda x:x[1])
    return newSentences

def combine_timelines(lines, names):
    """Combines two timelines and sorts them by date"""
    for i in range(len(lines)):
        newLine = lines[i].copy()
        newLine = [[j[0], names[i], j[1], j[2], j[3]] for j in newLine]
        lines[i] = newLine.copy()

    newLine = []
    for i in lines:
        newLine += i

    return sorted(newLine, key=lambda x:[x[4], x[2], x[3]])

def find_titles(soup):
    """Finds a list of titles, and when the person held these titles"""
    infobox = soup.find('table', attrs={'class':'infobox'})
    allRows = infobox.find_all('tr')

    titleList = []
    for i in range(len(allRows)-1):
        ###Titles are in <th> tags, are centered, take up the entire box, and
        ###have the special dash
        head = allRows[i].find('th')
        if(head and 'colspan' in head.attrs and head.attrs['colspan'] == '2'
           and SPAN_CHAR in allRows[i+1].text):
            titleList.append([citations(allRows[i].text), citations(allRows[i+1].text)])

    titleList = get_range(titleList)
    return titleList

def get_range(titleList):
    """Gets the start and end dates that the person held the title"""
    newList = []
    for i in titleList:
        print(i[1])
        ###The date starts with a capital Month, which will be the second match
        date = get_date_range(re.finditer(DATE_PATTERN, i[1]), i[1])
        ###Splits the date into the start date and the end date
        date = date.replace(',','').split(SPAN_CHAR)
        date = [j.strip().split(' ') for j in date]
        print(date)
        ###Gets a list of numbers for both dates
        date = [numerize_dates(j) for j in date]
        newList.append([i[0], date[0], date[1]])

    return newList

def get_date_range(iterator, string):
    """Gets the part of the string that has the date"""
    num = 0
    start, end = 0, None
    for i in iterator:
        num += 1
        if(num == 2):
            start = i.start()
        if(num == 4):
            end = i.end()

    return string[start:end]

def numerize_dates(dateList):
    """Turns a list of strings into a list of numbers that are [Month, Day Year]"""
    month, day, year = 0, 0, 0
    for i in range(len(dateList)):
        if(dateList[i].isnumeric()):
            if(i > 0 and dateList[i-1] == 'AD'):
                year = int(dateList[i])
            elif(i < len(dateList)-1 and dateList[i+1] == 'BC'):
                year = -int(dateList[i])
            elif(day == 0):
                day = int(dateList[i])
            else:
                year = int(dateList[i])
        elif(dateList[i] != 'BC' and dateList[i] != 'AD'):
            month = datetime.datetime.strptime(dateList[i], "%B").month
    
    return [month, day, year]
