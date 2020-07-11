#!/var/www/FlaskApp/FlaskApp/venv/bin/python3
#make an edit to the .bashrc file in /home/pi/.bashrc to the bottom python3 __init__.py
import RPi.GPIO as GPIO
from flask import Flask, flash, jsonify, redirect, render_template, request
import time
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
import mysql.connector
from mysql.connector import Error
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
change = 0
app = Flask(__name__)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@app.route('/run-tasks')
def run_tasks():
    app.apscheduler.add_job(func=turnon, trigger='date', id='1')
    return 'Scheduled several long running tasks.', 200

@app.route('/')
def index():
    return render_template("index.html")

try:
    connection = mysql.connector.connect(host='',
                                         database='sprinkler',
                                         user='user',
                                         password='user')
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)

except Error as e:
    print("Error while connecting to MySQL", e)
finally:
    if (connection.is_connected()):
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
# performs a check if the sprinkler needs to be turned on
def check():
    mydb = mysql.connector.connect(host='host',
        database='sprinkler',
        user='user',
        password='password')
    mycursor = mydb.cursor()
    mycursor.execute("SELECT `signal` FROM sprinkler WHERE `id` = 1")
    myresult = mycursor.fetchall()
    return myresult[0][0]
# if the signal to turn on is sent this will send a signal as well to prove it works 
def update(val):
    mydb = mysql.connector.connect(host='host',
        database='sprinkler',
        user='user',
        password='id')
    mycursor = mydb.cursor()
    sql = "UPDATE sprinkler SET `recieved` = {} WHERE `id` = 1".format(val)
    mycursor.execute(sql)
    mydb.commit()
    print(mycursor.rowcount, "record(s) affected") 
# function to turn on the desired pin and sprinkler switch, 
def sprinkler(number):
    led = number
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(led,GPIO.OUT)
    GPIO.output(led, GPIO.HIGH)
    print("switched")
# for some reason with the 5v relay, turning the led of gpio low still has a small voltage 
# therefore to turn it off do gpio cleanup and that removes the setup mode and eliminates the remaining voltage
def off():
    GPIO.cleanup()

change = 0

def turnon():
    state = check()
    global change
    if state == 1:
        if change == 0:
            print("Yes")
            update(1)
            change  = 1
            sprinkler(7)
        if change == 2:
            print("change to 1")
            off()
            update(1)
            change = 1
            sprinkler(7)
    elif state == 0 and (change == 1 or change == 2):
        print("No")
        update(0)
        change = 0
        off()
    elif state == 2:
        if change == 0:
            print("third")
            update(2)
            change = 2
            sprinkler(13)
        elif change == 1:
            print("change to 2")
            off()
            update(2)
            change = 2
            sprinkler(13)
            
    

def onon():
    print("Server is running")

shed = BlockingScheduler()

sched = BackgroundScheduler(daemon=True)
trigger = OrTrigger([ CronTrigger(minute='*')])
shed.add_job(turnon, trigger)
sched.add_job(turnon,trigger)
shed.start()
sched.start()

print("starting process")


if __name__== "__main__":
    sched.start()
    app.run(debug=True, use_reloader=False)
