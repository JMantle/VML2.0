import mysql.connector
import os

# Get database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        ssl_ca=os.getenv('DB_CA_PATH'),
        ssl_verify_cert=True
    )
    return conn


def resetLogins():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS logins")
    cursor.execute("""
        CREATE TABLE logins (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            team VARCHAR(255),
            captain BOOLEAN DEFAULT 0,
            admin BOOLEAN DEFAULT 0
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def resetTeams():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS teams")
    cursor.execute("""
        CREATE TABLE teams (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            place INT,
            mapwins INT,
            matchwins INT,
            captain VARCHAR(255),
            members TEXT,
            points INT,
            mmr INT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def makeTeam(name, mapwins, matchwins, captain, points, mmr):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO teams (name, mapwins, matchwins, captain, points, mmr) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (name, mapwins, matchwins, captain, points, mmr))
    conn.commit()
    cursor.close()
    conn.close()


def deleteTeam(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM teams WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()


def resetGames():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS games")
    cursor.execute("""
        CREATE TABLE games (
            id INT AUTO_INCREMENT PRIMARY KEY,
            home VARCHAR(255) NOT NULL,
            away VARCHAR(255) NOT NULL,
            winner VARCHAR(255),
            datetime DATETIME,
            homeplayers TEXT,
            awayplayers TEXT,
            other TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def makeGame(home, away, datetime):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (home, away, datetime) VALUES (%s, %s, %s)", (home, away, datetime))
    conn.commit()
    cursor.close()
    conn.close()


def deleteGame(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()


def editGame(attribute, value, id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE games SET {attribute} = %s WHERE id = %s", (value, id))
    conn.commit()
    cursor.close()
    conn.close()


def editPerms(username, captain, admin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE logins SET captain = %s, admin = %s WHERE username = %s", (captain, admin, username))
    conn.commit()
    cursor.close()
    conn.close()


def getPerms(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT captain, admin FROM logins WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result["captain"], result["admin"]


def resetRequests():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS requests")
    cursor.execute("""
        CREATE TABLE requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            teamname VARCHAR(255) NOT NULL,
            username VARCHAR(255),
            message TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def deleteRequest(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM requests WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()


def resetMessages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS messages")
    cursor.execute("""
        CREATE TABLE messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            message TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def deleteMessage(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()


def resetEvents():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS events")
    cursor.execute("""
        CREATE TABLE events (
            event VARCHAR(255) NOT NULL PRIMARY KEY
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


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
            mapwins = int(input("Map Wins: "))
            matchwins = int(input("Match Wins: "))
            captain = input("Captain: ")
            points = int(input("Points: "))
            mmr = int(input("MMR: "))
            makeTeam(name, mapwins, matchwins, captain, points, mmr)
        elif answer == "dt":
            id = input("ID of team to delete: ")
            deleteTeam(id)
        elif answer == "rg":
            resetGames()
        elif answer == "eg":
            id = input("ID: ")
            attribute = input("Attribute: ")
            value = input("Value: ")
            editGame(attribute, value, id)
        elif answer == "mg":
            home = input("Home: ")
            away = input("Away: ")
            datetime = input("Datetime: ")
            makeGame(home, away, datetime)
        elif answer == "lp":
            username = input("Username: ")
            captain = input("Captain: ")
            admin = input("Admin: ")
            editPerms(username, captain, admin)
        elif answer == "gp":
            username = input("Username: ")
            captain, admin = getPerms(username)
            print("Captain: ", captain)
            print("Admin: ", admin)
        elif answer == "dg":
            id = input("ID: ")
            deleteGame(id)
        elif answer == "rr":
            resetRequests()
        elif answer == "dr":
            id = input("ID: ")
            deleteRequest(id)
        elif answer == "rm":
            resetMessages()
        elif answer == "dm":
            id = input("ID: ")
            deleteMessage(id)
        elif answer == "re":
            resetEvents()


# Prevent accidental running
if __name__ == "__main__":
    main()