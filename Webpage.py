from flask import Flask, render_template, request, redirect
from Title import *

app = Flask(__name__)

@app.route('/')
def home_page():
    return render_template("index.html")

@app.route('/Placeholder', methods=['POST'])
def title_page():
    formNames = get_names()
    titles = []
    for i in formNames:
        if(i[1].strip() == ""):
            page = i[0]
        else:
            page = "{}_({})".format(i[0], i[1],lower())

        print(page)
        titles.append(find_titles(open_website(page)))

    print(titles)
    return render_template("results.html", total="FADFAFA")

def get_names():
    allNames = []
    numNames = len(request.form)//2
    for i in range(numNames):
        name, clar = request.form['term'+str(i+1)], request.form['clarify'+str(i+1)]
        allNames.append((name, clar))

    return allNames
