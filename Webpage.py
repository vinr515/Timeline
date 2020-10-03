from flask import Flask, render_template, request, redirect
from Base import *
from Title import find_titles
import timeline
import math
import datetime

app = Flask(__name__)
MIN_PERCENT = 1
TIMELINE_LINK = "https://en.wikipedia.org/wiki/Timeline"
@app.route('/')
def home_page():
    return render_template("index.html")

@app.route('/results', methods=['GET'])
def title_page():
    """Gets the input, and returns the page for the results"""
    formNames = get_names()
    ###Gets the input from the user from the form
    titles, lifeDates, names, onClickVars, links, eventDates = get_person_info(formNames)
    titleWord = "Timeline Project - " + ", ".join(names)

    return render_template("results.html", titles=titles, lifeDates=lifeDates,
                           names=names, onClickVars=onClickVars, links=links,
                           titleWord=[titleWord], eventDates=eventDates)

def get_names():
    """Returns a list of tuples, each tuple is one line of input"""
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
    titles, lifeStrings, names, onClickVars, links = [], [], [], [], []
    eventDates, lifeDates, index = [], [], 1
    for i in range(len(formNames)):
        page, thisName = get_page_name(formNames[i])
        soup = search_website(page)
        thisTitle, thisLifeString, thisLife = get_person_titles(soup, thisName)
        thisDates = get_person_dates(soup, thisLife, thisName)
        
        titles.append(thisTitle)
        lifeStrings.append(thisLifeString)
        names.append(thisName)
        links.append(WIKI_BASE + page)
        eventDates.append(thisDates)
        lifeDates.append(thisLife)
        
        click = "showTitle(this, {});".format(i+1)
        onClickVars.append([(click, str(k+index)) for k in range(len(thisTitle))])
        index += len(thisTitle)

    if(len(formNames) >= 2):
        ###Adds a timeline of when each person lived.
        bars, fullTime = common_titles(lifeDates, names)
        titles.append(bars)
        if(fullTime[1][1] == 32):
            fullTime = [fullTime[0], ["Present"]]
        fullTime = ['/'.join(map(str, j)) for j in fullTime]
        lifeStrings.append(fullTime)
        names.append("Common")
        links.append(TIMELINE_LINK)
        click = "showTitle(this, {});".format(len(formNames)+1)

        thisDates = [[] for j in range(len(bars))]
        eventDates.append(thisDates)
        onClickVars.append([(click, str(k+index)) for k in range(len(bars))])
        
    return titles, lifeStrings, names, onClickVars, links, eventDates

def get_person_dates(soup, life, name):
    """Gets the dates from the persons timeline"""
    dates, titles = timeline.timeline(soup=soup), find_titles(soup)
    titles = replace_blanks(scale_titles(titles, life, name), name)
    newTitles = [i[0] for i in adjust_size(titles)]

    if(len(newTitles) <= 0):
        finalDates = [[i[0] for i in dates]]
        return finalDates

    groupedDates = get_initial_dates(titles, dates)
    nextDates = get_final_dates(titles, groupedDates, newTitles)

    finalDates = []
    for i in nextDates:
        finalDates.append([j[0] for j in i])
        #finalDates.append([[j[0], round(100/len(i), 2)] for j in i])
        
    return finalDates

def get_initial_dates(titles, dates):
    """Splits the person's timeline dates into lists based on their titles"""
    groupedDates = []
    for i in range(len(titles)-1):
        startDate = float_dates(list(map(int, titles[i][2].split('/'))))
        endDate = float_dates(list(map(int, titles[i+1][2].split('/'))))
        line = [j for j in dates if(float_dates(j[1]) >= startDate and float_dates(j[1]) < endDate)]
        groupedDates.append(line)

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
        line.extend(groupedDates[i])
        if(titles[i][0] == newTitles[index]):
            newDates.append(line)
            line = []
            index += 1
            
    return newDates

def get_page_name(name):
    """Returns the links to each page"""
    if(name[1].strip() == ""):
        return name[0], name[0]
    return "{}_({})".format(name[0], name[1].lower()), name[0]

def get_person_titles(soup, name):
    """Returns everything about one person, with a soup object"""
    thisTitle, thisLife = find_titles(soup), timeline.lifespan(soup)
    
    if(type(thisLife[1]) == int):
        lifeString = ["/".join(map(str, thisLife[0])), "Present"]
        thisLife = (thisLife[0], [12,32,thisLife[1]])
    else:
        lifeString = ["/".join(map(str, i)) for i in thisLife]

    born, died = [float_dates(i) for i in thisLife]
    thisTitle = [i for i in thisTitle if float_dates(i[1]) >= born and
                 float_dates(i[2]) <= died]
        
    if(thisTitle):
        thisTitle = scale_titles(thisTitle, thisLife, name)
        thisTitle = adjust_size(replace_blanks(thisTitle, name))
        thisTitle = add_time_spans(thisTitle, lifeString[1])
    else:
        thisTitle = blank_title_bars(thisLife, name)

    return thisTitle, lifeString, thisLife

def scale_titles(titles, lifespan, name):
    """Scales the titles so that one long bar can be created for the webpage"""
    birth, died = lifespan
    newTitles = zero_dates(titles, birth)
    if(not(newTitles)): return []

    deathNum = float_dates(died)-float_dates(birth)
    
    scaleNum = 100/deathNum
    newTitles = sorted([[i[0], i[1]*scaleNum, i[2], i[3]] for i in newTitles], key=lambda x:x[1])    
    barVals = bar_values(newTitles, name, "{}/{}/{}".format(*birth), "{}/{}/{}".format(*died))
    
    return barVals

def zero_dates(titles, birth):
    """Turns all the [M, D, Y] dates into one number, starting from 0"""
    newTitles = []
    birthFloat = float_dates(birth)
    for i in range(len(titles)):
        startNum = float_dates(titles[i][1])
        endNum = float_dates(titles[i][2])

        startString = "/".join(map(str, titles[i][1]))
        endString = "/".join(map(str, titles[i][2]))
        
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
    num = year + (((month*30) + day)/365)

    return num
    
def bar_values(titles, name, birth, lastTime):
    """Gets all the values for the actual bar on the webpage"""
    barVals = [["", titles[0][1], birth]]
    lastTitle = ""
    for i in range(len(titles)-1):
        lastTitle = lastTitle.split(" ^^^ ")
        if(titles[i][2] == 1):
            lastTitle = lastTitle + [titles[i][0]]
        else:
            lastTitle.remove(titles[i][0])
        lastTitle = " ^^^ ".join([j for j in lastTitle if j])

        placeTitle = lastTitle.replace("^^^", "and")
        barVals.append([placeTitle, titles[i+1][1]-titles[i][1], titles[i][3]])

    if(sum([i[1] for i in barVals]) != 100):
        barVals.append(["", 100-sum([i[1] for i in barVals]), titles[-1][3]])

    return barVals

def replace_blanks(barVals, name):
    """Adds the person's name to all bars"""
    for i in range(len(barVals)):
        if(barVals[i][0] == ""):
            barVals[i][0] = name

    return barVals

def adjust_size(titles):
    """Removes bars/titles that were held for a short time"""
    newNum, newTitles = 0, []
    oldTitles = []
    for i in titles:
        if(i[1] < MIN_PERCENT):
            oldTitles.extend([[j, i[2]] for j in i[0].split(' and ')])
            newNum += i[1]
        else:
            oldTitles = [j for j in oldTitles if j[0] in i[0].split(' and ')]
            if(not(oldTitles)):
                newTitles.append([i[0], i[1]+newNum, i[2]])
            elif(len(oldTitles) == 1):
                newTitles.append([oldTitles[0][0], i[1]+newNum, oldTitles[0][1]])
            else:
                print("TOO BIG")
                print("During: ", oldTitles)
                raise ValueError("I have no idea what to do because there are two titles")
            oldTitles = []

    return newTitles

def add_time_spans(barVals, lastTime):
    """Adds the time spans for each bar/value that gets displayed"""
    newVals = []
    for i in range(len(barVals)-1):
        newName = "{} ({} - {})".format(barVals[i][0], barVals[i][2], barVals[i+1][2])
        width = str(barVals[i][1])+"%"
        newVals.append([newName, width])

    newName = "{} ({} - {})".format(barVals[-1][0], barVals[-1][2], lastTime)
    newVals.append([newName, str(barVals[-1][1])+"%"])
    return newVals

def blank_title_bars(lifespan, name):
    """Returns the values for the bars when a person doesn't have any titles"""
    startDate, endDate = "/".join(map(str, lifespan[0])), "/".join(map(str, lifespan[1]))
    string = "{} ({} - {})".format(name, startDate, endDate)
    if(lifespan[-1][1] == 32):
        string = "{} ({} - Present)".format(name, startDate)

    return [[string, "100.0%"]]

def common_titles(lifespans, names):
    """Makes a timeline that puts everyone's time period in perspective"""
    fakeTitles = []
    for i in range(len(names)):
        birth = lifespans[i][0]#list(map(int, lifespans[i][0].split('/')))
        died = lifespans[i][1]#list(map(int, lifespans[i][1].split('/')))
        fakeTitles.append([names[i], birth, died])
    
    allLifes = []
    for i in lifespans:
        #personLife = [list(map(int, j.split('/'))) for j in i]
        allLifes.extend(i)

    allLifes = sorted(allLifes, key=float_dates)
    
    bars = scale_titles(fakeTitles, (allLifes[0], allLifes[-1]), 'No one was alive')
    bars = replace_blanks(bars, 'No one was alive')
    bars = adjust_size(bars)
    bars = add_time_spans(bars, "/".join(map(str, allLifes[-1])))
    return bars, (allLifes[0], allLifes[-1])
