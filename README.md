# Sprinkler_system

## System Overview
Automatic Sprinkler System that uses Python, Flask, an open weather API to determine how much it has rained in a 4 day range. It stores the data in a MySQL database and the program references the database to determine daily weather to turn on the sprinkler or not. When the sprinkler turns on there is a Raspberry Pi that looks at the database every 2 minutes to see if a value is 0 or 1, if it changes to 1 it will change another row in the database to 1 and turn on the electronic sprinkler using a relay hooked up to GPIO pin on the Raspberry PI. After a set time (right now 20 min) the sprinkler system changes the database number to 0 and the Raspberry Pi turns off. 

## Twilio Features
The program also features Twilio text message system. The User can send a text message to the given number and get a list of options in the Parse message function. This includes being able to manually turn on the sprinkler system including individual valves. Due to home water pressure The program is designed to only have one valve on at a time so when a user or the system turns on a different valve it will turn off all the others to maintain proper pressure. The program allows for up to the same amount of valves as there are pins on the Raspbery Pi.

## Plotly Graph
The program also features a visable graph feature that shows the rain and sprinkler usage on a bar chart and water costs depending on the area.

![Plot Graph](/graph.jpg)
