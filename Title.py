from Base import *
import re

def find_titles(soup):
    """Finds a list of titles, and when the person held these titles"""
    try:
        infobox = soup.find('table', attrs={'class':'infobox'})
        allRows = infobox.find_all('tr')
    except AttributeError:
        return []

    titleList, headHold = [], None
    for i in range(len(allRows)):
        ###Titles are in <th> tags, are centered, take up the entire box, and
        ###have the special dash
        head = allRows[i].find('th')
        if(head and 'colspan' in head.attrs and head.attrs['colspan'] == '2'):
            headHold = allRows[i].text
        passMatchTest = (re.findall(MONTH_PATTERN, allRows[i].text) or
                         re.findall(YEAR_PATTERN, allRows[i].text))
        if(SPAN_CHAR in allRows[i].text and passMatchTest):
            titleList.append([citations(headHold), citations(allRows[i].text)])
     
    titleList = get_range(titleList)
    return titleList

def get_range(titleList):
    """Gets the start and end dates that the person held the title"""
    newList = []
    for i in titleList:
        ###The date starts with a capital Month, which will be the second match
        date = get_date_range(re.finditer(DATE_PATTERN, i[1]), i[1])
        if(not(SPAN_CHAR in date) or date == i[1]):
            date = re.findall(OLD_SPAN_PATTERN, i[1])[0]

        ###Splits the date into the start date and the end date
        date = date.replace(',','').split(SPAN_CHAR)
        ###Fake titles/dates usually have other things that mess everything up
        if(len(date) != 2):
            continue

        date = [j.strip().split(' ') for j in date]

        ###Gets a list of numbers for both dates
        date = [numerize_dates(j) for j in date]
        date = list(order_dates(*date))

        newList.append([i[0], date[0], date[1]])

    return newList

def get_date_range(iterator, string):
    """Gets the part of the string that has the date"""
    num = 0
    for i in iterator:
        num += 1
        if(num == 2):
            return string[i.start():]

    return string

def numerize_dates(dateList):
    """Turns a list of strings into a list of numbers that are [Month, Day Year]"""
    month, day, year = 0, 0, 0
    if(len(dateList) == 1):
        return [0, 0, int(dateList[0])]
    for i in range(len(dateList)):
        ###This gets the year/day
        if(dateList[i].isnumeric()):
            if(i > 0 and 'AD' in dateList[i-1]):
                year = int(dateList[i])
            elif(i < len(dateList)-1 and 'BC' in dateList[i+1]):
                year = -int(dateList[i])
                
            elif(day == 0):
                day = int(dateList[i])
            else:
                year = int(dateList[i])
                
        elif(not('BC' in dateList[i] or 'AD' in dateList[i])):
            try:
                month = datetime.datetime.strptime(dateList[i], "%B").month
            except ValueError:
                ###Sometimes there are notes besides the "In Office", that get included
                ###These aren't months, so they shouldn't fall in here
                pass
    
    return [month, day, year]

def order_dates(start, end):
    if(start == end):
        return start, end
    startVal = start[2] + (((start[0]*30)+start[1])/365)
    endVal = end[2] + (((end[0]*30)+end[1])/365)
    if(startVal < endVal):
        return start, end
    if(-startVal < endVal):
        return [start[0], start[1], -start[2]], end
    return start, [end[0], end[1], end[2]]
