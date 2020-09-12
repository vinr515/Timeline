from flask import Flask, render_template, request, redirect
from Base import *
from Title import find_titles
from timeline import lifespan
import math

app = Flask(__name__)
MIN_PERCENT = 1
@app.route('/')
def home_page():
    return render_template("index.html")

@app.route('/results', methods=['POST'])
def title_page():
    formNames = get_names()
    titles, lifeDates, names, onClickVars = get_person_info(formNames)

    return render_template("results.html", titles=titles, lifeDates=lifeDates,
                           names=names, onClickVars=onClickVars)

def get_names():
    allNames = []
    numNames = math.ceil(len(request.form)/2)
    
    for i in range(numNames):
        name, clar = request.form['term'+str(i+1)], request.form['clarify'+str(i+1)]
        allNames.append((name, clar))

    return allNames

def get_person_info(formNames):
    """Gets the name, lifespan, and titles given a list of [(name, clarify)]
for each person"""
    titles = []
    lifeDates = []
    names = []
    onClickVars = []
    index = 1
    for i in range(len(formNames)):
        j = formNames[i]
        if(j[1].strip() == ""):
            page = j[0]
            thisName = j[0]
        else:
            page = "{}_({})".format(j[0], j[1].lower())
            thisName = "{} ({})".format(j[0], j[1])

        soup = open_website(page)
        thisTitle, thisLife = find_titles(soup), lifespan(soup)
        thisTitle = scale_titles(thisTitle, thisLife, thisName)
        
        titles.append(thisTitle)
        lifeDates.append(thisLife)
        names.append(thisName)
        
        click = "showTitle(this, {});".format(i+1)
        onClickVars.append([(click, str(k+index)) for k in range(len(thisTitle))])
        index += len(thisTitle)

    return titles, lifeDates, names, onClickVars

def scale_titles(titles, lifespan, name):
    """Scales the titles so that one long bar can be created for the webpage"""
    birth, died = lifespan 
    newTitles = []
    for i in range(len(titles)):
        startNum = titles[i][1][2] + (((titles[i][1][0]*12)+titles[i][1][1])/365)
        endNum = titles[i][2][2] + (((titles[i][2][0]*12)+titles[i][2][1])/365)

        startString = "/".join(map(str, titles[i][1]))
        endString = "/".join(map(str, titles[i][2]))
        
        start = [titles[i][0], startNum, 1, startString]
        end = [titles[i][0], endNum, 0, endString]
        newTitles.extend([start, end])

    newTitles = [[i[0], i[1]-birth, i[2], i[3]] for i in newTitles]
    if(not(newTitles)): return []
    
    scaleNum = 100/max(newTitles, key=lambda x:x[1])[1]
    newTitles = sorted([[i[0], i[1]*scaleNum, i[2], i[3]] for i in newTitles], key=lambda x:x[1])

    barVals = bar_values(newTitles, name, "1/1/{}".format(birth), "12/31/{}".format(died))
    print(barVals[-1])
    return barVals
    
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
        barVals.append(["", 100-sum([i[1] for i in barVals])])

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
        newVals.append([newName, barVals[i][1]])

    newName = "{} ({} - {})".format(barVals[-1][0], barVals[-1][2], lastTime)
    newVals.append([newName, barVals[-1][1]])
    return newVals
