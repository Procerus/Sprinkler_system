import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def condition(number):
    """Look up condition for weather."""

    # Contact API
    try:
        response = requests.get(f"Open Weather API5")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        # for the [0] between list and main each number up to 39 adds three hours to forcast
        # weather conditions are clear sky few clouds scattered clouds broken clouds shower rain rain thunderstorm snow mist
        temp = quote["list"][number]["main"]["temp"]
        weather = quote["list"][number]["weather"][0]["main"]
        time = quote["list"][number]["dt_txt"]
        amount = 0
        try:
            if weather == "Rain":
                amount = quote["list"][number]["rain"]["3h"]
            else:
                amount = 0
        except (KeyError, TypeError, ValueError):
            pass
        return {
            "temp": temp,
            "weather": weather,
            "date": time,
            "amount": amount
        }
    except (KeyError, TypeError, ValueError):
        return None

