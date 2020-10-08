from flask import Flask, render_template, request, redirect
from Base import *
from Title import find_titles
import timeline
import math
import datetime

app = Flask(__name__)
MIN_PERCENT = 0.5
TIMELINE_LINK = "https://en.wikipedia.org/wiki/Timeline"
IMAGE_HEIGHT = 225
ERROR_MESS = ""
###Special new line character for the error message textarea
NEW_LINE = "&#13;&#10;"

@app.route('/')
def home_page():
    return render_template("index.html")

@app.route('/results', methods=['GET'])
def title_page():
    """Gets the input, and returns the page for the results"""
    formNames = get_names()
    ###Gets the input from the user from the form
    output = get_person_info(formNames)
    
    titles, lifeDates, names = output[0], output[1], output[2]
    onClickVars, links, eventDates = output[3], output[4], output[5]
    imageLinks = output[6]
    ###This is the website title that is displayed at the top in the tab
    titleWord = "Timeline Project - " + ", ".join(names)
    ERROR_MESS.replace("\n", NEW_LINE)

    return render_template("results.html", titles=titles, lifeDates=lifeDates,
                           names=names, onClickVars=onClickVars, links=links,
                           titleWord=[titleWord], eventDates=eventDates,
                           imageLinks=imageLinks, error=ERROR_MESS)

def get_names():
    """Returns a list of tuples, each tuple is one line of input/person"""
    allNames = []
    ###Each person has a name and a clarification
    numNames = math.ceil(len(request.args)/2)

    for i in range(numNames):
        name, clar = request.args['term'+str(i+1)], request.args['clarify'+str(i+1)]
        if(name.strip() != ''):
            allNames.append((name, clar))

    return allNames

def get_person_info(formNames):
    """Gets the name, lifespan, and titles given a list of [(name, clarify)]
for each person"""
    global ERROR_MESS
    titles, lifeStrings, names, onClickVars, links = [], [], [], [], []
    eventDates, lifeDates, imageLinks, index = [], [], [], 1
    baseTitles = []
    ###This method can't be broken up, because half of it is adding
    ###to the lists above
    for i in range(len(formNames)):
        ###Finds the person's page, gets his timeline events and titles
        page, thisName = get_page_name(formNames[i])
        soup = search_website(page)
        if(not(soup)):
            ERROR_MESS += "Could not find {}\n".format(thisName)
            continue
        ###Sometimes, a nickname is entered. Here, the name used in the website
        ###is switched to the person's real name
        thisName = soup.find('h1').text
        thisLifeString, thisLife = get_person_life(soup)
        try:
            line = find_titles(soup)
            baseTitles.append(line)
            thisTitle = get_person_titles(line, thisName, thisLife, thisLifeString)
        except:
            ERROR_MESS += "Error while finding titles for {}\n".format(thisName)
            continue
            
        try:
            thisDates = get_person_dates(soup, thisLife, thisName)
        except:
            ERROR_MESS += "Error while finding events for {}\n".format(thisName)
            continue
        
        titles.append(thisTitle)
        lifeStrings.append(thisLifeString)
        names.append(thisName)
        links.append(WIKI_BASE + page)
        eventDates.append(thisDates)
        lifeDates.append(thisLife)

        try:
            imageStats = list(get_image(soup, IMAGE_HEIGHT))
            imageLinks.append([imageStats[0], IMAGE_HEIGHT, imageStats[1]])
        except:
            ERROR_MESS += "Couldn't find image for {}\n".format(thisName)
            imageLinks.append("ALL")

        ###This is used for the Javascript on the website
        click = "showTitle(this, {});".format(i+1)
        onClickVars.append([(click, str(k+index)) for k in range(len(thisTitle))])
        index += len(thisTitle)

    
    ###There is no point for a common bar if we couldn't find the date for one person
    #if(len([j for j in lifeStrings if type(j) == list]) >= 2):
    if(len(baseTitles) >= 2):
        ###Adds a timeline of when each person lived.
        bars, fullTime = common_titles(lifeDates, names, baseTitles)
        titles.append(bars)
        lifeStrings.append(fullTime)
        names.append("Common")
        links.append(TIMELINE_LINK)
        click = "showTitle(this, {});".format(len(formNames)+1)

        ###There are no timeline events for the common timeline, so an empty list is passed
        thisDates = [[] for j in range(len(bars))]
        eventDates.append(thisDates)
        imageLinks.append("ALL")
        onClickVars.append([(click, str(k+index)) for k in range(len(bars))])
    
    return titles, lifeStrings, names, onClickVars, links, eventDates, imageLinks

def get_person_dates(soup, life, name):
    """Gets the dates from the persons timeline. Returns a list of lists.
Each second list is for one of the persons titles. """
    dates, titles = timeline.timeline(soup=soup), find_titles(soup)
    titles = replace_blanks(scale_titles(titles, life, name), name)
    ###newTitles removes any titles that were held for a few days or weeks
    newTitles = [i[0] for i in adjust_size(titles)]

    ###All events are placed in one list for those without titles
    if(len(newTitles) <= 0):
        finalDates = [[i[0] for i in dates]]
        return finalDates

    groupedDates = get_initial_dates(titles, dates)
    nextDates = get_final_dates(titles, groupedDates, newTitles)

    ###This only keeps the Wikipedia sentence, and not the date it happened. 
    finalDates = []
    for i in nextDates:
        finalDates.append([j[0] for j in i])
        
    return finalDates

def get_initial_dates(titles, dates):
    """Splits the person's timeline dates into lists based on their titles"""
    groupedDates = []
    for i in range(len(titles)-1):
        ###The dates are given as MM/DD/YYYY strings
        startDate = float_dates(list(map(int, titles[i][2].split('/'))))
        endDate = float_dates(list(map(int, titles[i+1][2].split('/'))))
        ###This takes everything that is in the middle of both dates
        line = [j for j in dates if(float_dates(j[1]) >= startDate and float_dates(j[1]) < endDate)]
        groupedDates.append(line)

    ###For the last title/part of the person's life
    groupedDates.append([j for j in dates if(float_dates(j[1]) >= endDate)])

    return groupedDates

def get_final_dates(titles, groupedDates, newTitles):
    """Makes the final number of titles equal the final number of timeline events
(Some titles are taken out, because they are small. Events during those times
are put in another category in this method)"""
    newTitles = [i[0] for i in adjust_size(titles)]
    newDates = []
    line = []
    index = 0
            
    for i in range(len(titles)):
        if(index >= len(newTitles)):
            break

        ###Adds every title to a hold variable (line), and adds line to
        ###the final variable (newDates) when the combined time of those titles
        ###is long enough
        line.extend(groupedDates[i])
        if(titles[i][0] == newTitles[index]):
            newDates.append(line)
            line = []
            index += 1
            
    return newDates

def get_page_name(name):
    """Adds the clarification to the name. Returns the search term and the name"""
    if(name[1].strip() == ""):
        return name[0], name[0]
    return "{}_({})".format(name[0], name[1].lower()), name[0]

def get_person_life(soup):
    """Returns a string MM/DD/YYYY birthday and a
    tuple of two [Month, Day, Year] lists"""
    thisLife = timeline.lifespan(soup)
    if(type(thisLife[1]) == int):
        lifeString = ["/".join(map(str, thisLife[0])), "Present"]
        thisLife = (thisLife[0], [12, 32, thisLife[1]])
    else:
        lifeString = ["/".join(map(str, i)) for i in thisLife]

    lifeString = [check_bc_time(i) for i in lifeString]
    if(thisLife[0][2] < -1000):
        lifeString = "No timespan"

    return lifeString, thisLife

def get_person_titles(thisTitle, name, thisLife, lifeString):
    """Returns a list of titles during a person's life, their lifespan as a
string, and their lifespan as a list ([Birth Month, Birth Day, BYear], (DM, DD, DY])"""
    born, died = [float_dates(i) for i in thisLife]
    thisTitle = [i for i in thisTitle if float_dates(i[1]) >= born and
                 float_dates(i[2]) <= died]
        
    if(thisTitle):
        thisTitle = scale_titles(thisTitle, thisLife, name)
        thisTitle = adjust_size(replace_blanks(thisTitle, name))
        thisTitle = add_time_spans(thisTitle, lifeString[1])
    else:
        thisTitle = blank_title_bars(thisLife, name)

    return thisTitle

def scale_titles(titles, lifespan, name):
    """Finds the length of each title (or combination of titles if the person held two at a time)
as a percent of their lifespan. """
    birth, died = lifespan
    newTitles = zero_dates(titles, birth)
    if(not(newTitles)): return []

    deathNum = float_dates(died)-float_dates(birth)

    ###This scales the titles so the person was born at 0.0 and died at 100.0
    scaleNum = 100/deathNum
    newTitles = sorted([[i[0], i[1]*scaleNum, i[2], i[3]] for i in newTitles], key=lambda x:x[1])    
    barVals = bar_values(newTitles, name, "{}/{}/{}".format(*birth), "{}/{}/{}".format(*died))
    
    return barVals

def zero_dates(titles, birth):
    """Turns all dates in the titles from [M, D, Y] to years since birth
(this number can, and probably will be a float)"""
    newTitles = []
    birthFloat = float_dates(birth)
    for i in range(len(titles)):
        if(len(titles[i][1]) == 1):
            print(titles[i])
        startNum = float_dates(titles[i][1])
        endNum = float_dates(titles[i][2])

        startString = "/".join(map(str, titles[i][1]))
        endString = "/".join(map(str, titles[i][2]))
        ###The date as a string is needed later, where it will be added to the title name
        start = [titles[i][0], startNum, 1, startString]
        end = [titles[i][0], endNum, 0, endString]
        newTitles.extend([start, end])

    newTitles = [[i[0], i[1]-birthFloat, i[2], i[3]] for i in newTitles]
    return newTitles

def float_dates(date):
    """Turns a date (list, [M, D, Y]) into one floating number"""
    try:
        if(len(date) != 3):
            print(len(date))
            print(date)
    except TypeError:
        print("TYPEERROR", list(date))
        
    month, day, year = date
    month -= 1
    ###This isn't exact, but it mostly works
    num = year + (((month*30) + day)/365)

    return num
    
def bar_values(titles, name, birth, lastTime):
    """Combines titles if two or more are held at the same time. """
    ###Start with an empty title (the person had no title/was a private citizen)
    ###If they did start with a title, it will be removed later for being too short
    barVals = [["", titles[0][1], birth]]
    lastTitle = ""
    for i in range(len(titles)-1):
        ### ^^^ is used as a place holder, because and can be used in a title
        lastTitle = lastTitle.split(" ^^^ ")
        ###1 means the person got that title, 0 means they dropped it
        if(titles[i][2] == 1):
            ###Add the title to the list of titles they have
            lastTitle = lastTitle + [titles[i][0]]
        else:
            lastTitle.remove(titles[i][0])
        lastTitle = " ^^^ ".join([j for j in lastTitle if j])

        placeTitle = lastTitle.replace("^^^", "and")
        barVals.append([placeTitle, titles[i+1][1]-titles[i][1], titles[i][3]])

    if(sum([i[1] for i in barVals]) != 100):
        ###This adds an empty title for the last part of the person's life
        barVals.append(["", 100-sum([i[1] for i in barVals]), titles[-1][3]])

    return barVals

def replace_blanks(barVals, name):
    """Adds the person's name to all empty (private citizen) titles"""
    for i in range(len(barVals)):
        if(barVals[i][0] == ""):
            barVals[i][0] = name

    return barVals

def adjust_size(titles):
    """Removes bars/titles that were held for a short time"""
    newTitles = []
    barLength = 0
    for i in titles:
        barLength += i[1]
        if(barLength >= MIN_PERCENT):
            newBar = [i[0], barLength] + i[2:]
            newTitles.append(newBar)
            barLength = 0

    return newTitles

def add_time_spans(barVals, lastTime):
    """Adds the time spans as a string for each bar/value that gets displayed"""
    newVals = []
    for i in range(len(barVals)-1):
        fromDate, toDate = check_bc_time(barVals[i][2]), check_bc_time(barVals[i+1][2])
        newName = "{} ({} - {})".format(barVals[i][0], fromDate, toDate)
        ###The width is a percentage of the screen that is used for the webpage
        width = str(barVals[i][1])+"%"
        newVals.append([newName, width])

    fromDate, toDate = check_bc_time(barVals[-1][2]), check_bc_time(lastTime)
    newName = "{} ({} - {})".format(barVals[-1][0], fromDate, toDate)
    newVals.append([newName, str(barVals[-1][1])+"%"])
    return newVals

def check_bc_time(timeString):
    """Returns a new string that uses B.C is the year is negative"""
    newTime = timeString.split('/')
    if(len(newTime) < 3 or "b.c" in newTime[2].lower() or int(newTime[2]) >= 0):
        return timeString
    string = '/'.join(newTime[:2] + [str(abs(int(newTime[2]))) + " B.C"])
    return string

def blank_title_bars(lifespan, name):
    """Returns the values for the titles when a person doesn't have any titles"""
    startDate, endDate = "/".join(map(str, lifespan[0])), "/".join(map(str, lifespan[1]))
    string = "{} ({} - {})".format(name, startDate, endDate)
    if(lifespan[-1][1] == 32):
        string = "{} ({} - Present)".format(name, startDate)

    return [[string, "100.0%"]]

def common_titles(lifespans, names, baseTitles):
    """Combines everyone's titles and lifespans to create one big timeline"""
    combTitles = []
    for i in range(len(baseTitles)):
        for j in baseTitles[i]:
            line = j.copy()
            line[0] = "{} was ".format(names[i]) + line[0]
            combTitles.append(line.copy())

    combSpan = []
    for i in lifespans:
        combSpan.extend(i)

    combSpan = sorted(combSpan, key=float_dates)
    bars = scale_titles(combTitles, (combSpan[0], combSpan[-1]), "No one held any titles")
    bars = replace_blanks(bars, "No one held any titles")
    bars = adjust_size(bars)
    bars = add_time_spans(bars, "/".join(map(str, combSpan[-1])))

    ###32 is used as a placeholder for the present day (no month has 32 days)
    fullTime = [combSpan[0], combSpan[-1]]
    if(fullTime[1][1] == 32):
        fullTime = [fullTime[0], ["Present"]]
    fullTime = ['/'.join(map(str, j)) for j in fullTime]
    return bars, fullTime
