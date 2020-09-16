from flask import Flask, render_template, request, redirect
from Base import *
from Title import find_titles
from timeline import lifespan
import math
import datetime

app = Flask(__name__)
MIN_PERCENT = 1
@app.route('/')
def home_page():
    return render_template("index.html")

@app.route('/results', methods=['GET'])
def title_page():
    formNames = get_names()
    titles, lifeDates, names, onClickVars, links = get_person_info(formNames)
    titleWord = "Timeline Project - " + ", ".join(names)

    return render_template("results.html", titles=titles, lifeDates=lifeDates,
                           names=names, onClickVars=onClickVars, links=links,
                           titleWord=[titleWord])

def get_names():
    allNames = []
    numNames = math.ceil(len(request.args)/2)

    for i in range(numNames):
        name, clar = request.args['term'+str(i+1)], request.args['clarify'+str(i+1)]
        allNames.append((name, clar))

    return allNames

def get_person_info(formNames):
    """Gets the name, lifespan, and titles given a list of [(name, clarify)]
for each person"""
    titles, lifeDates, names, onClickVars, links = [], [], [], [], []
    index = 1
    for i in range(len(formNames)):
        page, thisName = get_page_name(formNames[i])
        soup = open_website(page)
        thisTitle, thisLife = get_person_titles(soup, thisName)

        titles.append(thisTitle)
        lifeDates.append(thisLife)
        names.append(thisName)
        links.append(WIKI_BASE + page)
        
        click = "showTitle(this, {});".format(i+1)
        onClickVars.append([(click, str(k+index)) for k in range(len(thisTitle))])
        index += len(thisTitle)

    print("Common: ", lifeDates)

    return titles, lifeDates, names, onClickVars, links

def get_page_name(name):
    """Returns the links to each page"""
    if(name[1].strip() == ""):
        return name[0], name[0]
    return "{}_({})".format(name[0], name[1].lower()), name[0]

def get_person_titles(soup, name):
    """Returns everything about one person, with a soup object"""
    thisTitle, thisLife = find_titles(soup), lifespan(soup)
    
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
    else:
        thisTitle = blank_title_bars(thisLife, name)

    return thisTitle, lifeString

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
    month, day, year = date
    month -= 1
    num = year + (((month*30) + day)/365)

    return num
    
def bar_values(titles, name, birth, lastTime):
    """Gets all the values for the actual bar on the webpage"""
    barVals = [["", titles[0][1], birth]]
    lastTitle = ""
    for i in range(len(titles)-1):
        lastTitle = lastTitle.split(" and ")
        if(titles[i][2] == 1):
            lastTitle = lastTitle + [titles[i][0]]
        else:
            lastTitle.remove(titles[i][0])
        lastTitle = " and ".join([j for j in lastTitle if j])
        barVals.append([lastTitle, titles[i+1][1]-titles[i][1], titles[i][3]])

    if(sum([i[1] for i in barVals]) != 100):
        barVals.append(["", 100-sum([i[1] for i in barVals]), titles[-1][3]])

    barVals = replace_blanks(barVals, name)
    barVals = adjust_size(barVals)
    barVals = add_time_spans(barVals, lastTime)
    return barVals

def replace_blanks(barVals, name):
    for i in range(len(barVals)):
        if(barVals[i][0] == ""):
            barVals[i][0] = name

    return barVals

def adjust_size(titles):
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

    ###This is the day. 32 is used to show that it isn't really a day,
    ###and actually the present
    if(lastTime.split("/")[1] == "32"):
        lastTime = "Present"
    newName = "{} ({} - {})".format(barVals[-1][0], barVals[-1][2], lastTime)
    newVals.append([newName, barVals[-1][1]])
    return newVals

def blank_title_bars(lifespan, name):
    """Returns the values for the bars when a person doesn't have any titles"""
    startDate, endDate = "/".join(map(str, lifespan[0])), "/".join(map(str, lifespan[1]))
    string = "{} ({} - {})".format(name, startDate, endDate)
    if(lifespan[-1][1] == 32):
        string = "{} ({} - Present)".format(name, startDate)

    return [[string, "100.0%"]]
