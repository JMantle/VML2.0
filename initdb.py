import sqlite3

def resetLogins():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("""

        DROP TABLE IF EXISTS logins

    """)

    c.execute("""

        CREATE TABLE logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            team TEXT,
            captain BOOLEAN DEFAULT 0,
            admin BOOLEAN DEFAULT 0
        )

    """)

    connect.commit()
    connect.close()

def resetTeams():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("""

        DROP TABLE IF EXISTS teams

    """)

    c.execute("""

        CREATE TABLE teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            place INT,
            mapwins INT,
            matchwins INT,
            captain TEXT,
            members TEXT,
            points INT,
            mmr INT
        )

    """)

    connect.commit()
    connect.close()

def makeTeam(name, mapwins, matchwins, captain, points, mmr):  # feels OO to me but i dont think making it OO will help
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("INSERT INTO teams (name, mapwins, matchwins, captain, points, mmr) VALUES (?, ?, ?, ?, ?, ?)", (name, mapwins, matchwins, captain, points, mmr))

    connect.commit()
    connect.close()

def deleteTeam(id):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DELETE FROM teams WHERE id = ?", (id,))

    connect.commit()
    connect.close()

def resetGames():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DROP TABLE IF EXISTS games")

    c.execute("""

        CREATE TABLE games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            home TEXT NOT NULL,
            away TEXT NOT NULL,
            winner TEXT,
            datetime DATETIME,
            homeplayers TEXT,
            awayplayers TEXT,
            other TEXT
        )

    """)

    connect.commit()
    connect.close()

def makeGame(home, away, datetime):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()
    c.execute("INSERT INTO games (home, away, datetime) VALUES (?, ?, ?)", (home, away, datetime))  
    connect.commit()
    connect.close()

def deleteGame(id):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DELETE FROM games WHERE id = ?", (id,))

    connect.commit()
    connect.close()


def editGame(attribute, value, id):
    connect = sqlite3.connect("database.db")
    c= connect.cursor()
    c.execute(f"UPDATE games SET {attribute} = ? WHERE id = ?", (value, id))
    connect.commit()
    connect.close()

def editPerms(username, captain, admin):
    connect = sqlite3.connect("database.db")
    c= connect.cursor()
    c.execute("UPDATE logins SET captain = ?, admin = ? WHERE username = ?", (captain, admin, username))
    connect.commit()
    connect.close()

def getPerms(username):
    connect = sqlite3.connect("database.db")
    c= connect.cursor()
    (captain, admin) = c.execute("SELECT captain, admin FROM logins WHERE username = ?", (username,)).fetchone()
    connect.close()
    return captain, admin

def resetRequests():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DROP TABLE IF EXISTS requests")

    c.execute("""

        CREATE TABLE requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teamname TEXT NOT NULL,
            username TEXT,
            message TEXT
        )

    """)

    connect.commit()
    connect.close()

def deleteRequest(id):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DELETE FROM requests WHERE id = ?", (id,))

    connect.commit()
    connect.close()

def resetMessages():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DROP TABLE IF EXISTS messages")

    c.execute("""

        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            message TEXT
        )

    """)

    connect.commit()
    connect.close()

def deleteMessage(id):
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DELETE FROM messages WHERE id = ?", (id,))

    connect.commit()
    connect.close()

def resetEvents():
    connect = sqlite3.connect("database.db")
    c = connect.cursor()

    c.execute("DROP TABLE IF EXISTS events")

    c.execute("""

        CREATE TABLE events (
            event TEXT NOT NULL PRIMARY KEY
        )

    """)

    connect.commit()
    connect.close()


def main():
    loop = True
    while loop:
        answer = input(">")
        if answer == "rl":
            resetLogins()
        elif answer == "e":
            loop = False
        elif answer == "rt":
            resetTeams()
        elif answer == "mt":
            name = input("Name: ")
            place = int(input("Place: "))
            games = int(input("Games: "))
            wins = int(input("Wins: "))
            captain = input("Captain: ")
            points = int(input("Points: "))
            makeTeam(name, place, games, wins, captain, points)
        elif answer == "dt":
            id = input("id of team to delete: ")
            deleteTeam(id)
        elif answer == "rg":
            resetGames()
        elif answer == "eg":
            id = input("Id: ")
            attribute = input("attribute: ")
            value = input("value: ")
            editGame(attribute, value, id)
        elif answer == "mg":
            home = input("home: ")
            away = input("away: ")
            datetime = input("datetime: ")
            makeGame(home, away, datetime)
        elif answer == "lp":
            username = input("username: ")
            captain = input("captain: ")
            admin = input("admin: ")
            editPerms(username, captain, admin)
        elif answer == "gp":
            username = input("username: ")
            (captain, admin) = getPerms(username)
            print("captain: ", captain)
            print("admin: ", admin)
        elif answer == "dg":
            id = input("id: ")
            deleteGame(id)
        elif answer == "rr":
            resetRequests()
        elif answer == "dr":
            id = input("id: ")
            deleteRequest(id)
        elif answer == "rm":
            resetMessages()
        elif answer == "dm":
            id = input("id: ")
            deleteMessage(id)
        elif answer == "re":
            resetEvents()


# prevent accidental running
if __name__ == "__main__":
    main()