from flask import Flask, render_template, redirect, request, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import pytz
from initdb import makeTeam, deleteTeam, makeGame, deleteGame, deleteRequest, deleteMessage, resetLogins, resetEvents, resetMessages, resetRequests 
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

global first


# flask app
app = Flask(__name__)
app.secret_key = "secretKey"   ## ENTER SECRET KEY HERE



# sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
key = json.loads(os.getenv("key"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(key, scope)
client = gspread.authorize(creds)

# open sheet
sheet = client.open_by_key("1J1Ay6lxrv0B-IBOLBgZF70dSyywNey3IOQboO1tn25Q").sheet1

# sort teams by mmr on sheet
def sortTeams():
    # get teams table from sheet
    data = sheet.get_all_values()
    # sort by mmr
    teams = data[1:7]
    # bubble sort teams because data size is very low
    swap = True
    while swap:
        swap = False
        for i in range(0, len(teams) - 1):
            if int(teams[i][5]) > int(teams[i+1][5]):
                teams[i], teams[i + 1] = teams[i + 1], teams[i]
                swap = True
    # put sorted teams back into sheet
    sheet.update("A2:F7", teams)

    return teams
    


# get database connection and format
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn 



# LOGIN AND SIGNUP

# handle attempted log in
@app.route("/loginSubmit", methods=["POST"])
def inputSubmitted():
    #get data
    username = request.form["username"]
    attemptedPassword = request.form["password"]
    #search to see if account exists
    conn = get_db_connection()
    found = conn.execute("SELECT password FROM logins WHERE username = ?", (username,)).fetchone()
    conn.close()
    if found:
        #check password against one stored
        if check_password_hash(found[0], attemptedPassword):
            #set session variables
            session["loggedIn"] = True
            session["username"] = username
            #give user permissions if they need them
            (captain, admin) = checkPerms(username)
            session["captain"] = captain
            session["adminperms"] = admin
            #take user to index page
            return redirect("/index")
        else:
            #incorrect password
            flash("wrong password")
    else:
        #account does not exists
        flash("no accounts with this username")
    #allow user to try again on same page
    return redirect("/loginPage")

# check account perms
def checkPerms(username):
    #get users permissions from database
    conn = get_db_connection()
    (captain, admin) = conn.execute("SELECT captain, admin FROM logins WHERE username = ?", (username,)).fetchone()
    conn.close()
    #cast them to bool
    return bool(captain), bool(admin)


# send user to sign up page
@app.route("/goToSignUp", methods=["GET"])
def goToSignUp():
    return render_template("signUpPage.html")

# handle attempted sign up
@app.route("/signUpSubmit", methods=["POST"])
def signUp():
    #get username and check it is valid (no commas)
    username = request.form["username"]
    if ',' in username:
        flash('Username cannot contain commas.')
        return redirect('/signUpPage')
    else:
        #make sure username noot taken
        conn = get_db_connection()
        found = conn.execute("SELECT password FROM logins WHERE username = ?", (username,)).fetchone()
        if found:
           conn.close()
           flash("Username already taken")
           return render_template("/signUpPage.html")
        else:
            #hash password and put all data in database
            hashedPassword = generate_password_hash(request.form["password"])
            conn.execute("INSERT INTO logins (username, password) VALUES (?, ?)", (username, hashedPassword))

            #check for first user
            if g.first:
                #give them admin perms
                conn.execute("UPDATE logins SET admin = 1 WHERE username = ?", (username,))
                session["adminperms"] = True
                g.first = False
            conn.commit()
            conn.close()
            #let user log in
            return redirect("/loginPage")
    
# send user to log in page
@app.route("/loginPage", methods=["GET"])
def loginPage():
    return render_template("loginPage.html")



# STANDINGS

#fetch standings and put them in place order
def getStandings():
    #get teams table from sheet
    data = sheet.get_all_values()
    
    #extract teams from data
    teams = data[1:7]

    return teams






# GAMES

#get upcoming game data 
def getUpcomingGames(team):

    #get data
    data = sheet.get_all_values()
    #get amount of games
    gamesNumber = data[18][0]
    #check for games
    if gamesNumber == "0":
        return None
    else:
        #get games
        games = data[20:20 + int(gamesNumber)]

        #detect if it needs to be a specific team
        if len(team) > 0:
            tempGames = games
            games = []
            for game in tempGames:
                if game[0] == team or game[1] == team:
                    games.append(game)
        return games

#localise the time specific to the user
def utc_to_local(utc_dt, timezone_str):
    local_tz = pytz.timezone(timezone_str)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_dt

#get games and change the times to the user's timezone
def getTimezonedGames(team):
    #get times and timezone
    games_data = getUpcomingGames(team)
    user_timezone_str = session.get('timezone') 

    #format datetimes to normalize
    for game in games_data:
        if game[2] != "-":
            #convert string to datetime
            date, time = game[2].split("_")
            day, month, year = date.split("-")
            game[2] = f"{year}-{month}-{day} {time}:00"

    updated_games = []

    #localize each game
    for game in games_data:
        if game[2] != "-":
            #get utc datetime
            utc_dt = datetime.strptime(game[2], '%Y-%m-%d %H:%M:%S')

            #localize it if able to get user's timezone
            if user_timezone_str:
                #give game local datetime
                game[2] = utc_to_local(utc_dt, user_timezone_str).strftime('%Y-%m-%d %H:%M:%S')
                # set abbreviated timezone
                session["abbreviatedTimezone"] = utc_dt.astimezone(pytz.timezone(user_timezone_str)).tzname()

            else:
                #give user UTC times if not able to get timezone
                session["abbreviatedTimezone"] = "UTC"

        #put games back together again
        updated_games.append(game)

    return updated_games


# TEAM

#find team by name
def findTeam(teamName):
    #get teams
    teams = getStandings()
    #find team in standings
    for team in teams:
        if team[0] == teamName:
            return team
    return None

#find team row
def findTeamRow(teamName):
    #get teams
    teams = getStandings()
    #find team in standings
    for i in range(0, len(teams)):
        if teams[i][0] == teamName:
            return i + 2 # because first is header and not 0 indexed
    return None

#show all team data on specific team
@app.route("/showTeam/<string:teamName>")
def team(teamName):

    #get team and set stats
    team = findTeam(teamName)
    stats = {
                "place": findTeamRow(teamName) - 1,
                "name": team[0],
                "mapwins": int(team[2]),
                "matchwins": int(team[3]),
                "captain": team[5],
                "members": team[6],
                "points": int(team[1]),
                "mmr": int(team[4])
            }

    #get upcoming games for that team
    games = getTimezonedGames(teamName)

    #get database connection
    conn = get_db_connection()

    #get membership requests for captain if the user is the captain
    if session.get("loggedIn") and stats["captain"] == session["username"]:
        requests = conn.execute("SELECT * FROM requests WHERE teamname = ?", (stats["name"],)).fetchall()
        conn.close()
        return render_template("team.html", stats=stats, games=games, captain=True, member=True, requests=requests)
    else:
        #take team members
        members = stats["members"] if stats["members"] is not None else ""
        #get if the user has already requested membership 
        requested = bool(conn.execute("SELECT 1 FROM requests WHERE username = ? AND teamname = ?", (session["username"], stats["name"])).fetchone())
        #decide whether to show the request membership button or not.
        if (session["loggedIn"] and session["username"] in members) or  requested:
            member = True
        else:
            member = False
        conn.close()

        return render_template("team.html", stats=stats, games=games, captain=False, member=member)
    
#handle user requesting membership
@app.route("/requestMembership/<string:teamName>/<string:username>", methods=["POST"])
def requestMembership(teamName, username):
    #get message
    message = request.form.get("message")
    #put it in database
    conn = get_db_connection()
    conn.execute("INSERT INTO requests (teamname, username, message) VALUES (?, ?, ?)", (teamName, username, message))
    

    # enter event into event database for the bot to see
    # conn.execute("INSERT INTO events (event) VALUES (?)", (teamName,))

    conn.commit()
    conn.close()

    return redirect("/showTeam/" + teamName)

# MANAGE TEAM

#handle manage team being clicked
@app.route("/manageTeam")
def manageTeam():
    #get teams
    teams = getStandings()

    #if all fails, just send em to apex (hopefully it dont)
    teamName = "Apex"

    for team in teams:
        #check if user is captain of the team
        if team[5] == session["username"]:
            #get team name
            teamName = team[0]
            break
    return redirect("/showTeam/" + teamName)

#handle removing member from team
@app.route("/removeFromTeam/<string:teamName>/<string:member>", methods=["POST"])
def removeFromTeam(teamName, member):

    #get team
    team = findTeam(teamName)
    members = team[6] if team[6] else ""

    #remove sepcific member

    #place each member in a list
    membersString = members
    members = []
    while len(membersString) > 0:
        comma = membersString.find(",")
        if comma == -1:
            members.append(membersString)
            membersString = ""
        else:
            members.append(membersString[:comma])
            membersString = membersString[comma + 2:]
    #remove the chosen member
    members.remove(member)

    #put back into string to store
    membersString = ""

    #add all items except last with comma
    for i in range(0, len(members) - 1):
        membersString = membersString + members[i] + ", "
    
    #add last item without comma
    membersString = membersString + members[len(members) - 1]
    
    #get row of team
    row = findTeamRow(teamName)

    #put it back into sheet
    sheet.update_cell(row + 2, 7, membersString)

    return redirect("/manageTeam")

#handle adding members
@app.route("/addMember/<string:teamName>", methods=["POST"])
def addMember(teamName):
    #get name
    name = request.form.get("name").strip()

    #get current members
    team = findTeam(teamName)
    members = team[6] if team[6] else ""

    #add to string
    if members != "":
        #add to end if members already there
        members += ", " + name
    else:
        #become the first member
        members = name

    #update sheet
    row = findTeamRow(teamName)
    sheet.update_cell(row + 2, 7, members)

    #return to managing team
    return redirect("/manageTeam")

#handle assigning players to games                                              (might need idk yet)
#@app.route("/assignPlayers/<int:gameId>/<string:teamName>", methods=["POST"])
#def assignPlayers(gameId, teamName):
#    #get data
#    players = request.form.get("players").strip()
#    conn = get_db_connection()
#
#    #figure out whether team is home or away
#    side = conn.execute("SELECT home FROM games WHERE id = ?", (gameId,)).fetchone()
#    if side[0] == teamName:
#        #home team
#        conn.execute("UPDATE games SET homeplayers = ? WHERE id = ?", (players, gameId))
#    else:
#        #away team
#        conn.execute("UPDATE games SET awayplayers = ? WHERE id = ?", (players, gameId))
#
#    conn.commit()
#    conn.close()
#
#    #return to manage team
#    return redirect("/manageTeam")

#handle accepting membership requests
@app.route("/acceptRequest/<int:id>", methods=["POST"])
def acceptRequest(id):
    conn = get_db_connection()

    #get request
    request = conn.execute("SELECT * FROM requests WHERE id = ?", (id,)).fetchone()
    teamName = request["teamname"]
    name = request["username"]

    #get current members
    team = findTeam(teamName)
    members = team[6] if team[6] else ""

    #add to string
    if members != "":
        #add to end if members already there
        members += ", " + name
    else:
        #become the first member
        members = name

    #update sheet
    row = findTeamRow(teamName)
    sheet.update_cell(row + 2, 7, members)

    #delete request
    deleteRequest(id)

    return redirect("/manageTeam")

#handle declining request
@app.route("/declineRequest/<int:id>", methods=["POST"])
def declineRequest(id):
    #delete it
    deleteRequest(id)
    return redirect("/manageTeam")

# ADMIN

#handle going to admin page
@app.route("/admin")
def admin():
    #get data
    teams = getStandings()
    games = getTimezonedGames("")
    users = getUsers()
    #get messages
    conn = get_db_connection()
    messages = conn.execute("SELECT * FROM messages").fetchall()
    conn.close()
    #load page
    return render_template("admin.html", teams=teams, games=games, users=users, messages=messages) 

# users

#get all users
def getUsers():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM logins").fetchall()
    conn.close()
    return users

#handle updating user permissions
@app.route("/updateUser/<string:id>", methods=["POST"])
def updateUser(id):
    conn = get_db_connection()

    #invert user's captaincy
    if "makeCaptain" in request.form:
        row = conn.execute("SELECT captain FROM logins WHERE id = ?", (id,)).fetchone()
        current = row["captain"]
        conn.execute("UPDATE logins SET captain = ? WHERE id = ?", (0 if current else 1, id))

    #invert user's admin permission
    elif "makeAdmin" in request.form:
        row = conn.execute("SELECT admin FROM logins WHERE id = ?", (id,)).fetchone()
        current = row["admin"]
        conn.execute("UPDATE logins SET admin = ? WHERE id = ?", (0 if current else 1, id))

    conn.commit()
    conn.close()
    return redirect("/admin")

# teams

##handle updating team data                                    (might be needed idk yet)
#@app.route("/updateTeam/<int:id>", methods=["POST"])
#def updateTeam(id):
#    conn = get_db_connection()
#
#    #get inputted data
#    name = request.form.get("name").strip()
#    mapWins = request.form.get("mapwins").strip()
#    matchWins = request.form.get("matchwins").strip()
#    captain = request.form.get("captain").strip()
#    members = request.form.get("members").strip()
#    points = request.form.get("points").strip()
#    mmr = request.form.get("mmr").strip()
#
#    #get previous data
#    team = conn.execute("SELECT * FROM teams WHERE id = ?", (id,)).fetchone()
#
#    #update data if inputted, otherwise result to previous data
#    updatedName = name if name else team['name']
#    updatedMapWins = mapWins if mapWins else team['mapwins']
#    updatedMatchWins = matchWins if matchWins else team['matchwins']
#    updatedCaptain = captain if captain else team['captain']
#    updatedMembers = members if members else team["members"]
#    updatedPoints = points if points else team['points']
#    updatedmmr = mmr if mmr else team["mmr"]
#
#    #return to database
#    conn.execute("UPDATE teams SET name = ?, mapwins = ?, matchwins = ?, captain = ?, members = ?, points = ?, mmr = ? WHERE id = ?", (updatedName, updatedMapWins, updatedMatchWins, updatedCaptain, updatedMembers, updatedPoints, updatedmmr, id))
#
#    conn.commit()
#    conn.close()
#
#    #update their places (mmr could be changed affecting the order of the teams)
#    sortTeams()
#
#    return redirect("/admin")
#
##handle creation of teams                       (might be needed idk yet)
#@app.route("/createTeam", methods=["POST"])
#def createTeam():
#
#    #get data
#    name = request.form.get("name").strip()
#    mapwins = request.form.get("mapwins").strip()
#    matchwins = request.form.get("matchwins").strip()
#    captain = request.form.get("captain").strip()
#    points = request.form.get("points").strip()
#    mmr = request.form.get("mmr").strip()
#
#    #make team using the data
#    makeTeam(name, mapwins, matchwins, captain, points, mmr)
#    
#    #update teams places
#    sortTeams()
#
#    return redirect("/admin")
#
##handle deleting team
#@app.route("/deleteTeam/<int:id>", methods=["POST"])
#def deleteTeamRoute(id):
#    #delete team
#    deleteTeam(id)
#    return redirect("/admin")
#
# games

##handle updating game
#@app.route("/updateGame/<int:id>", methods=["POST"])
#def updateGame(id):
#    conn = get_db_connection()
#
#    #get data
#    home = request.form.get("home").strip()
#    away = request.form.get("away").strip()
#    datetime = request.form.get("datetime").strip()
#    homePlayers = request.form.get("homeplayers").strip()
#    awayPlayers = request.form.get("awayplayers").strip()
#    other = request.form.get("other").strip()
#    
#    #get previous data
#    game = conn.execute("SELECT * FROM games WHERE id = ?", (id,)).fetchone()
#
#    #update data if there is new data, otherwise use previous data
#    updatedHome = home if home else game['home']
#    updatedAway = away if away else game['away']
#    updatedDatetime = datetime if datetime else game['datetime']
#    updatedHomePlayers = homePlayers if homePlayers else game['homeplayers']
#    updatedAwayPlayers = awayPlayers if awayPlayers else game["awayplayers"]
#    updatedOther = other if other else game['other']
#
#    #put it back in database
#    conn.execute("UPDATE games SET home = ?, away = ?, datetime = ?, homeplayers = ?, awayplayers = ?, other = ? WHERE id = ?", (updatedHome, updatedAway, updatedDatetime, updatedHomePlayers, updatedAwayPlayers, updatedOther, id))
#
#    conn.commit()
#    conn.close()
#
#    return redirect("/admin")
#
##handle deleting game
#@app.route("/deleteGame/<int:id>", methods=["POST"])
#def deleteGameRoute(id):
#    #delete game
#    deleteGame(id)
#    return redirect("/admin")
#
##handle creating a game
#@app.route("/createGame", methods=["POST"])
#def createGame():
#
#    #get data
#    home = request.form.get("home").strip()
#    away = request.form.get("away").strip()
#    datetime = request.form.get("datetime").strip()
#
#    #make game
#    makeGame(home, away, datetime)
#
#    #update places
#    sortTeams()
#    
#    return redirect("/admin")

#handle deleting messages
@app.route("/deleteMessage/<int:id>", methods=["POST"])
def deleteMessageRoute(id):
    #delete message
    deleteMessage(id)
    return redirect("/admin")




# INDEX

#handle home page
@app.route("/index")
def index():
    #get data
    teams = getStandings()
    games = getTimezonedGames("")

    return render_template("index.html", teams=teams, games=games)

#contact
@app.route("/submitMessage", methods=["POST"])
def submitMessage():
    #get data
    name = request.form.get("name").strip()
    email = request.form.get("email").strip()
    message = request.form.get("message").strip()

    #put in database
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)", (name, email, message))

    #update events for bot
    # conn.execute("INSERT INTO events (event) VALUES (?)", ("message",))

    conn.commit()
    conn.close()

    #handle user
    flash("Message Submitted")
    return redirect("/index")

#log out
@app.route("/logOut")
def logOut():
    session.clear()
    return redirect("/")

# LOADED

@app.route("/loaded")
def loaded():
    # SET TIMEZONE
    timezone = request.args.get("timezone")
    if timezone:
        session["timezone"] = timezone
    #load index
    return index()

# MAIN

@app.route("/")
def root():
    
    # SESSION VARIABLES

    if "loggedIn" not in session:
        session["loggedIn"] = False
    if "username" not in session:
        session["username"] = ""
    if "captain" not in session:
        session["captain"] = False
    if "adminperms" not in session:
        session["adminperms"] = False

    # LOAD

    return render_template("load.html")


@app.before_first_request
def initializeFirst():
    g.first = True


#prevent accidental running
if __name__ == "__main__":

    resetLogins()
    resetMessages()
    resetRequests()
    resetEvents()

    first = True

    #run app
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)

    

# entry point
def runApp():
    port = int(os.environ.get("PORT", 8080)) 
    app.run(host="0.0.0.0", port=port)

