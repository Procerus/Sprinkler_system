import os, time, atexit, smtplib, mysql.connector, io, base64, json, plotly
from mysql.connector import Error
from datetime import datetime, date, timedelta
from string import Template
from cs50 import SQL
from flask_ask import Ask, statement, convert_errors
from twilio.rest import Client
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, flash, jsonify, redirect, render_template, request, session, send_file
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd, condition
from twilio.twiml.messaging_response import MessagingResponse
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Configure application
app = Flask(__name__)
# ask = Ask(app, '/')
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Time zone of the aws environment is off so i changed the timezone to chicago time
os.environ["TZ"] = "America/Chicago"

account_sid = 'ID HERE OR USE VIRTUAL'
auth_token = 'TOKEN HERE FOR TWILIO'


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CSrun50 Library to use SQLite database
db = SQL("sqlite:///var/www/finance/finance/finance.db")
# db = SQL("sqlite:///var/www/finance/finance.db")

@app.route("/")
@login_required
def index():
 return render_template("weather.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # make sure the user enters in username and passwords
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Please enter username and password")
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords did not match")
        user = db.execute("SELECT * FROM users WHERE username=:name", name=request.form.get("username"))
        if not user:
            db.execute("INSERT INTO users (id,username, hash) VALUES(NULL,'" + request.form.get("username") +
                   "','"+generate_password_hash(request.form.get("password"))+"')")
        else:
            return apology("Username Taken",400)
        return render_template("login.html")
    else:
        return render_template("register.html")


#route for viewing the sprinkler system
@app.route("/weather")
#add log in required if multiple have it
def weather():
    #idnumber just to display the sprinkler system in row one
    idnumber = 39
    # add here str(session["user_id"])
    #weather = db.execute("SELECT * FROM  weather WHERE userid = "+str(session["user_id"]))
    weather = db.execute("SELECT weather FROM weather WHERE id = :name", name=idnumber)
    temp = db.execute("SELECT temp FROM weather WHERE id = :name", name=idnumber)
    weather = weather[0].get("weather")
    #change the json version of temperature to the Farenheight
    temp = temp[0].get("temp")
    temp = int(temp)
    temp = float(temp - 273.15) * (9/5) + 32
    temp = round(temp,2)
    ##here use fig if you want matlib use bar for plotly
    #fig = create_figure()
    bar = plotly_figure()
    # Convert plot to PNG image
    #pngImage = io.BytesIO()
    #FigureCanvas(fig).print_png(pngImage)
    
    # Encode PNG image to base64 string
    #pngImageB64String = "data:image/png;base64,"
    #pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
    #do calculations for amount of gal and cost per month to display on website

    total_used = total_month()
    gal = int(total_used) * 17
    cost = round(((int(gal) / 1000) * 22),2)

    return render_template("weather.html", weather = weather, temp = temp, total = total_used, gal = gal, cost = cost, plot = bar)

#18.215.206.79
@app.route("/sms", methods=['GET', 'POST'])
def sms_reply():
    """Respond to incoming messages with a friendly SMS."""
    # Start our response
    body = request.values.get('Body')
    sender = request.values.get('From')
    print(sender)
    print(body)
    # it collects the data from the incomming text message as body and sender and inputs it through a parser function
    parsetext(body,sender)
    return ""




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

def read_template(filename):
    with open(filename, 'r', encoding='utf-8') as template_file:
        template_file_content = template_file.read()
    return Template(template_file_content)


def weathercheck():
    now = datetime.now()
    daynow = now.strftime('%Y-%m-%d')
    '''
    I use Mysql and a local database to learn the methods for both. This function cycles the weather
    for a period of 8 days 4 before the current day and 4 after for every 3 hours due to API restrictions
    I store the data for the weather in the database on the current weather prediction and store the 
    predictions after the current date. If the weather information is past 4 days the weather will be deleted in 
    this table but will remain in a differnt table that specializes in history
    '''
    mydb = mysql.connector.connect(host='HOST ADDRESS FOR MYSQL DATABASE',
        database='sprinkler',
        user='dbmasteruser',
        password='UWECphysics')
    mycursor = mydb.cursor()
    #deletes the oldest weather record for glen ellyn
    db.execute("DELETE FROM weather WHERE id=0")
    #shifts all the records from the stored weather hours up one so it adds the current weather to the list and saves it for the past 4 days
    db.execute("UPDATE weather SET id =id-1 WHERE id >0 ORDER BY weather.Id DESC LIMIT 200")
    weather = condition(39)
    db.execute("INSERT INTO weather(id,userid,weather,date,temp,rain) VALUES(:number,:userid,:weather,:date,:temp,:rain)",number=78, userid=5, weather=weather["weather"], date=weather["date"], temp=weather["temp"],rain=weather["amount"])
    for i in range(0,39):
        idnumber = i + 39
        sql="SELECT `rain` FROM sprinkler.usage WHERE `currentdate` ='{}'".format(daynow)
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        rain_num = 0
        if mycursor.rowcount == 0:
            temp_num = condition(0)["temp"]
            sql = "INSERT INTO `sprinkler`.`usage`(`rain`,`temp`,`timeused`,`userid`,`currentdate`)VALUES({},{},{},{},'{}')".format(0,temp_num,0,0,daynow)
            mycursor.execute(sql)
            mydb.commit()
            print("{} record(s) affected".format(mycursor.rowcount))  
        else:
            rain_num = myresult[0][0]
            temp = condition(0)["temp"]
            sql="SELECT `temp` FROM sprinkler.usage WHERE `currentdate` ='{}'".format(daynow)
            mycursor.execute(sql)
            myresult = mycursor.fetchall()
            temp_num = myresult[0][0]
            temp_num = (int(temp_num) + temp) / 2
            temp_num = float(temp_num - 273.15) * (9/5) + 32
            temp_num = round(temp_num,2)
        if i == 0:
            weather = condition(0)
            if weather["weather"] == "Rain":
                rain_num = float(rain_num) + (float(weather["amount"]) / 25.4)
            sql = "UPDATE sprinkler.usage SET `rain` = {}, `temp` = {} WHERE `currentdate` = '{}'".format(rain_num,temp_num, daynow)
            mycursor.execute(sql)
            mydb.commit()
		
        weather = condition(i)
        db.execute("UPDATE weather SET weather=:weather, temp=:temp, date=:date, rain=:rain WHERE id=:number",weather=weather["weather"], date=weather["date"], temp=weather["temp"], number=idnumber, rain=weather["amount"])

def raincheck():    
    """
    This function is ran every day at a specific time to check if the rain has properly watered the lawn/plants
    I have it set for 1.5 in a week and that number can be changed.

    """
    mydb = mysql.connector.connect(host='DATABASE HOST HERE',
        database='sprinkler',
        user='USERNAME',
        password='Password')

    #check to make sure the signal doesn't conflict with other signals, (once on will not turn on again unless turned off first)
    mycursor = mydb.cursor()
    now = datetime.now()
    monthnumber = int(now.strftime("%m"))
    hour = int(now.strftime("%H"))
    minute = int(now.strftime("%M"))
    second = int(now.strftime("%S"))
    monthday = int(now.strftime("%d"))
    daynow = now.strftime('%Y-%m-%d')
    #get days of the month for loop for graph
    days_in_month = (date(int(now.strftime("%Y")), monthnumber + 1, 1) - date(int(now.strftime("%Y")), monthnumber, 1)).days
    print("Days listed here")
    x_axis = []
    x_subaxis = []
    y_axis = []
    rain_axis = []
    
    for i in range(1,int(days_in_month) + 1):
        graph_days = (now - timedelta(days = monthday) + timedelta(days= i)).strftime('%Y-%m-%d')
        width = 10 / days_in_month
        mycursor.execute("SELECT `timeused` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
        myresult = mycursor.fetchall()
        if mycursor.rowcount != 0:
            timeused = myresult[0][0]
            x_axis.append(i)
            x_subaxis.append(i + 0.5)
            y_axis.append(int(timeused))
        else:
            x_axis.append(i)
            x_subaxis.append(i/2)
            y_axis.append(0)
        if i < monthday + 1:
            mycursor.execute("SELECT `rain` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
            rainresult = mycursor.fetchall()
            if mycursor.rowcount != 0:
                rain_num = rainresult[0][0]
                print(rain_num)
                rain_axis.append(float(rain_num))
            else:
                rain_axis.append(0)
        else:
            weather = db.execute("SELECT rain FROM weather where date LIKE :date", date="2020-06-" + str(i) + "%")
            total_rain = 0.0
            for j in weather:
                total_rain = total_rain + float(j['rain'])
            rain_axis.append(float(total_rain)  / 25.4)
            total_rain = 0.0
    total_inches = 0
    for i in range(monthday - 3, monthday + 3):
        try:
            if i < monthday:
                total_inches += float(y_axis[i])
            total_inches += float(rain_axis[i])
        except:
            pass
    if total_inches > 2: 
        message="Daily Update: The Lawn will have enough water."
        textmessage(message)
    elif total_inches <= 2:
        message="Daily Update: The Lawn will not get enough water, Sprinkler will turn on!.",
        textmessage(message)
        update(1)
        #The skd is a scheduled event that is turned off, if the ssytem turns on the event starts and turns off the system in 20 min
        skd.resume()

def activate():
    # this is a basic funciton to determine the connectivity of the database
    try:
        connection = mysql.connector.connect(host='host address here',
            database='sprinkler',
            user='user',
            password='password')
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print("You're connected to database: ", record)

    except Error as e:
        textmessage("Error while connecting to MySQL")
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

def textmessage(messages, sender = '+TWILIO NUMBER HERE'):
    #twilio text server, it sends a text message through twilio
    client = Client(account_sid, auth_token)
    message = client.messages \
        .create(
            body=messages,
            from_='+TWILIO NUMBER HERE',
            to= sender
         )
    print(message.sid)

def update(val=0):
    #Database connection updating the website database for the pi to read
    mydb = mysql.connector.connect(host='HOST ADDRESS HERE',
        database='sprinkler',
        user='user',
        password='password')
    print(val)
    print(skd.state)
    
    #check to make sure the signal doesn't conflict with other signals, (once on will not turn on again unless turned off first)
    mycursor = mydb.cursor()
    mycursor.execute("SELECT `signal` FROM sprinkler WHERE `id` = 1")
    myresult = mycursor.fetchall()
    check = myresult[0][0]
    print("this is check {}".format(check))
    
    mycursor = mydb.cursor()
    sql = "UPDATE sprinkler SET `signal` = {} WHERE `id` = 1".format(val)
    mycursor.execute(sql)
    mydb.commit()
    print("{} record(s) affected".format(mycursor.rowcount)) 


    #Getting current datetime for update and comparison.
    now = datetime.now()

    #2020-04-22 18:36:35.220625  format
    monthday = int(now.strftime("%d"))
    hour = int(now.strftime("%H"))
    minute = int(now.strftime("%M"))
    second = int(now.strftime("%S"))
    daynow = now.strftime('%Y-%m-%d')
    now = now.strftime('%Y-%m-%d %H:%M:%S')
    #compare the values if it is on or not
    if val == 1 and skd.state == 2 and check == 0:
        sql = "UPDATE sprinkler SET `time` = '{}' WHERE `id` = 1".format(now)
        print("This is the date".format(now))
        mycursor.execute(sql)
        print("Set signal to {}".format(val))
        mydb.commit()
        print("{} record(s) affected".format(mycursor.rowcount)) 
        check = 1

    if val == 0 and skd.state == 2 and check == 1:
        skd.pause()
        print("Set signal to {}".format(val))
        mycursor = mydb.cursor()
        sql="SELECT `time` FROM sprinkler WHERE `id` = 1"
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        newtime = myresult[0][0]
        newmonthday = int(newtime.strftime("%d"))
        newhour = int(newtime.strftime("%H"))
        newminute = int(newtime.strftime("%M"))
        newsecond = int(newtime.strftime("%S"))
        if newmonthday == 1:
            monthday = 1
        totalminutes = (monthday - newmonthday) * 3600 + (hour - newhour) * 60 + (minute - newminute ) + (second - newsecond) /60
        sql="SELECT `timeused` FROM sprinkler.usage WHERE `currentdate` ='{}'".format(daynow)
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        print(totalminutes)
        check = 0
        # this is a check to make sure that the day exists in the data table if not it creates one through insertion
        if mycursor.rowcount == 0:
            sql = "INSERT INTO `sprinkler`.`usage`(`timeused`,`currentdate`)VALUES({},'{}')".format(totalminutes,daynow)
            mycursor.execute(sql)
            mydb.commit()
            print("{} record(s) affected".format(mycursor.rowcount)) 

        else:
            oldtime = int(myresult[0][0])
            print("this is the old time {}".format(oldtime))
            
            sql = "UPDATE sprinkler.usage SET `timeused` = {} WHERE `currentdate` = '{}'".format(oldtime + totalminutes, daynow)
            mycursor.execute(sql)
            mydb.commit()
            print("{} record(s) affected".format(mycursor.rowcount)) 

def tempresponse(sender):
    # if a user wants the current temperature
    idnumber = 0
    weather = db.execute("SELECT weather FROM weather WHERE id = :name", name=idnumber)
    temp = db.execute("SELECT temp FROM weather WHERE id = :name", name=idnumber)
    weather = weather[0].get("weather")
    temp = temp[0].get("temp")
    temp = int(temp)
    temp = float(temp - 273.15) * (9/5) + 32
    temp = round(temp,2)
    textmessage("Hello, The current weather is " + weather + " and the temperature is " + str(temp) + "F",sender)

def helpmessage():
    help = "Help:Weather Now to get current weather information, \n Turn off to turn on sprinkler \n Turn on to turn on sprinkler."
    textmessage(help)

def parsetext(message,sender):
    # function to parse text messages that are incomming
    message = message.lower()
    print(message)
    # message is the incomming message and below are the various checks depending on what is wanted.
    if message == "weather now":
        print("weather update")
        tempresponse(sender)
    elif message == "turn on one":
        if sender == '+Phone Number':
            update(1)
            print("turn on")
            textmessage("Turning first Sprinkler on", sender)
        else:
            textmessage("No system assigned to account", sender)
    elif message == "turn on two":
        if sender == '+Phone Number':
            update(2)
            print("turn on")
            textmessage("Turning second Sprinkler on", sender)
        else:
            textmessage("No system assigned to account", sender)
    elif message == "turn off":
        if sender == '+Phone Number':
            update(0)
            print("turn off")
            textmessage("Turning Sprinkler off", sender)
        else:
            textmessage("No system assigned to account", sender)

    else:
        helpmessage()
        print("help")

def create_figure():
    # Generate plot
    mydb = mysql.connector.connect(host='host address',
        database='sprinkler',
        user='user',
        password='pass')

    #check to make sure the signal doesn't conflict with other signals, (once on will not turn on again unless turned off first)
    mycursor = mydb.cursor()
    now = datetime.now()
    monthnumber = int(now.strftime("%m"))
    hour = int(now.strftime("%H"))
    minute = int(now.strftime("%M"))
    second = int(now.strftime("%S"))
    monthday = int(now.strftime("%d"))
    daynow = now.strftime('%Y-%m-%d')
    #get days of the month for loop for graph
    days_in_month = (date(int(now.strftime("%Y")), monthnumber + 1, 1) - date(int(now.strftime("%Y")), monthnumber, 1)).days
    print("Days listed here")
    x_axis = []
    x_subaxis = []
    y_axis = []
    rain_axis = []

    for i in range(1,int(days_in_month) + 1):
        graph_days = (now - timedelta(days = monthday) + timedelta(days= i)).strftime('%Y-%m-%d')
        width = 10 / days_in_month
        mycursor.execute("SELECT `timeused` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
        myresult = mycursor.fetchall()
        if mycursor.rowcount != 0:
            timeused = myresult[0][0]
            print(timeused)
            x_axis.append(i)
            x_subaxis.append(i + 0.5)
            y_axis.append(int(timeused))
        else:
            x_axis.append(i)
            x_subaxis.append(i/2)
            y_axis.append(0)
        mycursor.execute("SELECT `rain` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
        rainresult = mycursor.fetchall()
        if mycursor.rowcount != 0:
            rain_num = rainresult[0][0]
            print(rain_num)
            rain_axis.append(int(rain_num))
        else:
            rain_axis.append(0)
    
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.set_title("Sprinkler System")
    axis.set_xlabel("Day of the month")
    axis.set_ylabel("Minutes ran/Cost")
    axis.grid()
    data = {"Sprinkler":y_axis,"Rain":rain_axis,}
    sprinkler_bar = axis.bar(x_axis, y_axis, width, color='b')
    rain_bar = axis.bar(x_subaxis, rain_axis, width, color='r')
    axis.legend( (sprinkler_bar[0],rain_bar[0]),("Sprinkler","Rain") )
    return fig

def total_month():
    # Generate plot
    mydb = mysql.connector.connect(host='Host address',
        database='sprinkler',
        user='user',
        password='password')

    #check to make sure the signal doesn't conflict with other signals, (once on will not turn on again unless turned off first)
    mycursor = mydb.cursor()
    now = datetime.now()
    monthnumber = int(now.strftime("%m"))
    hour = int(now.strftime("%H"))
    minute = int(now.strftime("%M"))
    second = int(now.strftime("%S"))
    monthday = int(now.strftime("%d"))
    daynow = now.strftime('%Y-%m-%d')
    #get days of the month for loop for graph
    days_in_month = (date(int(now.strftime("%Y")), monthnumber + 1, 1) - date(int(now.strftime("%Y")), monthnumber, 1)).days
    print("Days listed here")
    total_time = 0
    for i in range(1,int(days_in_month) + 1):
        graph_days = (now - timedelta(days = monthday) + timedelta(days= i)).strftime('%Y-%m-%d')
        mycursor.execute("SELECT `timeused` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
        myresult = mycursor.fetchall()
        if mycursor.rowcount != 0:
            total_time = total_time + int(myresult[0][0])
    return total_time

def plotly_figure():
    # Generate plot
    mydb = mysql.connector.connect(host='Host Address',
        database='sprinkler',
        user='User',
        password='password')

    #check to make sure the signal doesn't conflict with other signals, (once on will not turn on again unless turned off first)
    mycursor = mydb.cursor()
    now = datetime.now()
    monthnumber = int(now.strftime("%m"))
    hour = int(now.strftime("%H"))
    minute = int(now.strftime("%M"))
    second = int(now.strftime("%S"))
    monthday = int(now.strftime("%d"))
    daynow = now.strftime('%Y-%m-%d')
    #get days of the month for loop for graph
    days_in_month = (date(int(now.strftime("%Y")), monthnumber + 1, 1) - date(int(now.strftime("%Y")), monthnumber, 1)).days
    print("Days listed here")
    x_axis = []
    x_subaxis = []
    y_axis = []
    rain_axis = []

    for i in range(1,int(days_in_month) + 1):
        graph_days = (now - timedelta(days = monthday) + timedelta(days= i)).strftime('%Y-%m-%d')
        width = 10 / days_in_month
        mycursor.execute("SELECT `timeused` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
        myresult = mycursor.fetchall()
        if mycursor.rowcount != 0:
            timeused = myresult[0][0]
            x_axis.append(i)
            x_subaxis.append(i + 0.5)
            y_axis.append(int(timeused))
        else:
            x_axis.append(i)
            x_subaxis.append(i/2)
            y_axis.append(0)
        if i < monthday + 1:
            mycursor.execute("SELECT `rain` FROM sprinkler.usage WHERE `currentdate` = '{}'".format(graph_days))
            rainresult = mycursor.fetchall()
            if mycursor.rowcount != 0:
                rain_num = rainresult[0][0]
                print(rain_num)
                rain_axis.append(float(rain_num))
            else:
                rain_axis.append(0)
        else:
            weather = db.execute("SELECT rain FROM weather where date LIKE :date", date="2020-06-" + str(i) + "%")
            total_rain = 0.0
            for j in weather:
                total_rain = total_rain + float(j['rain'])
            rain_axis.append(float(total_rain)  / 25.4)
            total_rain = 0.0
            
  

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x_axis,
                y=y_axis,
                name='Sprinkler',
                marker_color='rgb(55, 83, 109)'
                ))
    fig.add_trace(go.Bar(x=x_axis,
                y=rain_axis,
                name='rain',
                marker_color='rgb(26, 118, 255)'
                ))
    try:
        fig.add_annotation(
                x=monthday,
                y=y_axis[monthday],
                text="Today Usage")
        fig.update_annotations(dict(
                    xref="x",
                    yref="y",
                    showarrow=True,
                    arrowhead=7,
                    ax=0,
                    ay=-40
        ))
    except:
        print("Last day of the Month")
    fig.update_layout(
        title='Sprinkler Usage with Rain Tracking',
        xaxis_tickfont_size=9,
        yaxis=dict(
            title='Minutes Ran / Rain Inches',
            titlefont_size=16,
            tickfont_size=14,
        ),
        legend=dict(
            x=0,
            y=1.0,
            bgcolor='rgba(255, 255, 255, 0)',
            bordercolor='rgba(255, 255, 255, 0)'
        ),
        barmode='group',
        bargap=0.15, # gap between bars of adjacent location coordinates.
        bargroupgap=0.1 # gap between bars of the same location coordinate.
    )

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

now = datetime.now()
current_time = now.strftime("%H")
raining = False

#message= "Server is up!"
#textmessage(message)
# here is the list of Cron Triggers that schedules the program 
#Note for some reason the server running on AWS restarts randomly in the middle of the night
#I had a textmessage funciton here to display when the server booted however I would get a text
#everynight so I removed the function. However even with the server resetting it has not missed a function call
activate()
sched = BackgroundScheduler(daemon=True, timezone="America/Chicago")
skd = BackgroundScheduler(daemon=True, timezone="America/Chicago")
weatherschd = BackgroundScheduler(daemon=True, timezone="America/Chicago")
trigger = OrTrigger([ CronTrigger(hour='0,3,6,9,12,15,18,21')])
raintrigger = OrTrigger([ CronTrigger(hour='10')])
checktrigger = OrTrigger([ CronTrigger(minute='20')])
skd.add_job(update, checktrigger)
weatherschd.add_job(weathercheck, trigger)
sched.add_job(raincheck,raintrigger)
sched.start()
weatherschd.start()
skd.start()
skd.pause()
print("Current Time =", current_time)



# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

atexit.register(lambda: cron.shutdown(wait=False))

