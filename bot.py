import discord
from discord.ext import commands
import gspread
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
from app import getStandings, getUpcomingGames, get_db_connection
import json
import os
from aiohttp import web
import sys

# For Unix systems (Linux/macOS):
if sys.platform != 'win32':
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


# aiohttp web server
routes = web.RouteTableDef()

@routes.get("/")
async def index(request):
    return web.Response(text="Hello from aiohttp!")

app = web.Application()
app.add_routes(routes)




# Setup Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Setup Google Sheets access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
key = json.loads(os.getenv("key"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(key, scope)
client = gspread.authorize(creds)

# Open the sheet by ID
sheet = client.open_by_key("1J1Ay6lxrv0B-IBOLBgZF70dSyywNey3IOQboO1tn25Q").sheet1

# take standings and format them for standings channel
def formatStandings():
    standings = getStandings()
    embed = discord.Embed(title="Current Standings", color=discord.Color.blue())
    count = 0
    for team in standings:
        count += 1
        embed.add_field(name=f"{count} **{team[0]}**", value=f"{team[1]} Points| {team[2]} Map wins | {team[3]} Match wins | {team[4]} MMR", inline=False)
    return embed

# find teams from game id
def findTeamsFromGame(id):
    # find from only the games part of the sheet
    gameAmount = int(sheet.cell(19, 1).value)
    games = sheet.get_values(f"A21:F{21 + gameAmount}")
    for game in games:
        if game[5] == str(id):
            return game[0], game[1]
        

# check for messages in db for the bot
async def checkEvents():
    while True:
        await asyncio.sleep(10)

        conn = get_db_connection()
        events = conn.execute("SELECT * FROM events").fetchall()

        teamNames = ["Apex", "Sneaky Snakes", "TFO", "Galaxy Guardians", "Xenon", "741"]

        if not events:
            continue
        for event in events:
            if event[0] == "message":
                guild = bot.guilds[0]
                for channel in guild.text_channels:
                    if channel.name == "standings":
                        await channel.send("new message for admins")
            elif event[0] in teamNames:
                captainRole = discord.utils.get(guild.roles, name=f"{event[0]} Captain")
                guild = bot.guilds[0]
                for channel in guild.text_channels:
                    if channel.name == "standings":
                        await channel.send(f"new request for {captainRole.mention}")
            else:
                print(f"Unknown event: {event[0]}")
        # clear events
        conn.execute("DELETE FROM events")

        conn.commit()
        conn.close()









# NORMAL COMMANDS


#help command
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help", description="List of commands", color=discord.Color.blue())
    embed.add_field(name="!help", value="Shows this message", inline=False)
    embed.add_field(name="!info COMMAND", value="Shows information about a command e.g. !info standings (only admins can use the admin ones)", inline=False)
    embed.add_field(name="**ADMIN** !makegame Team1 v Team2", value="Creates a new game between Team1 and Team2", inline=False)
    embed.add_field(name="**CAPTAIN** !setdatetime ID DD-MM-YYYY_HH:MM", value="Sets the date and time for the game with the given id SET ALL TIMES WITH UTC", inline=False)
    embed.add_field(name="**CAPTAIN** !setteam ID PLAYER1, PLAYER2, PLAYER3 etc", value="Sets the team for the game with the given id", inline=False)
    embed.add_field(name="**CAPTAIN/ADMIN** !result ID Game1 Game2 Game3", value="Sets the result for the game with the given id, where each game is in the format X:Y (e.g. 1:0)", inline=False)
    embed.add_field(name="!standings", value="Shows the current standings", inline=False)
    embed.add_field(name="!games", value="Shows all upcoming games ALL TIMES WILL BE UTC", inline=False)
    embed.add_field(name="!website", value="Shows the website link", inline=False)

    await ctx.send(embed=embed)

#info command
@bot.command()
async def info(ctx, commandName: str):
    commandName = commandName.lower()
    embed = discord.Embed(title=f"Info for {commandName}", color=discord.Color.blue())

    if commandName == "help":
        embed.description = "Shows a list of commands and their descriptions"
        embed.add_field(name="Usage", value="!help", inline=False)
        embed.add_field(name="Example", value="!help", inline=False)
        embed.set_footer(text="this one is pretty simple")
    elif commandName == "info":
        embed.description = "Shows information about a command"
        embed.add_field(name="Usage", value="!info COMMAND_NAME", inline=False)
        embed.add_field(name="Example", value="!info standings", inline=False)
        embed.set_footer(text="do not include the ! in the command name")
    elif commandName == "makegame":
        embed.description = "Creates a new game between two teams **ADMIN ONLY**"
        embed.add_field(name="Usage", value="!makegame Team1 v Team2", inline=False)
        embed.add_field(name="Example", value="!makegame Apex v Sneaky Snakes", inline=False)
        embed.set_footer(text="write the names of the teams exactly as they are in the sheet, including spaces and capitalization and only put v in the middle (not vs)")
    elif commandName == "setdatetime":
        embed.description = "Sets the date and time for the game with the given id **CAPTAIN ONLY**"
        embed.add_field(name="Usage", value="!setdatetime ID DD-MM-YYYY_HH:MM", inline=False)
        embed.add_field(name="Example", value="!setdatetime 1 01-01-2025_12:00", inline=False)
        embed.set_footer(text="captains should get a DM with the id and all times are UTC. The other captain or an admin need to confirm the time by reacting to the message with a ✅ or deny with ❌")
    elif commandName == "setteam":
        embed.description = "Sets the team for the game with the given id **CAPTAIN ONLY**"
        embed.add_field(name="Usage", value="!setteam ID PLAYER1, PLAYER2, PLAYER3 etc", inline=False)
        embed.add_field(name="Example", value="!setteam 1 AIMORE, Squirt, Spoon", inline=False)
        embed.set_footer(text="captains should get a DM with the id and player names cannot contain commas (they are used to separate players)")
    elif commandName == "result":
        embed.description = "Sets the result for the game with the given id **CAPTAIN OR ADMIN ONLY**"
        embed.add_field(name="Usage", value="!result ID HomeScore1:AwayScore1 HomeScore2:AwayScore2 HomeScore3:AwayScore3", inline=False)
        embed.add_field(name="Example", value="!result 1 0:9 5:9 9:8", inline=False)
        embed.set_footer(text="If a captain uses this command, the other captain needs to confirm the result by reacting to the message with a ✅ or deny with ❌. If an admin uses this command, it will be set without confirmation. The scores must be in home:away order")
    elif commandName == "standings":
        embed.description = "Shows the current standings"
        embed.add_field(name="Usage", value="!standings", inline=False)
        embed.add_field(name="Example", value="!standings", inline=False)
        embed.set_footer(text="not much to say about this one, it just shows the standings")
    elif commandName == "games":
        embed.description = "Shows all upcoming games"
        embed.add_field(name="Usage", value="!games", inline=False)
        embed.add_field(name="Example", value="!games", inline=False)
        embed.set_footer(text="all times are UTC (the website will show the times in your local timezone)")
    elif commandName == "website":
        embed.description = "Shows the website link"
        embed.add_field(name="Usage", value="!website", inline=False)
        embed.add_field(name="Example", value="!website", inline=False)
        embed.set_footer(text="the website has more information and you can request membership to teams there")
    else:
        embed.description = "Command not found."

    await ctx.send(embed=embed)
    # that felt front endy

#standings command
@bot.command()
async def standings(ctx):
    embed = formatStandings()
    await ctx.send(embed=embed)

#games command
@bot.command()
async def games(ctx):
    games = getUpcomingGames("")
    if not games:
        await ctx.send("No upcoming games found.")
        return

    embed = discord.Embed(title="Upcoming Games", color=discord.Color.green())
    for game in games:
        embed.add_field(name=f"{game[1]} vs {game[2]}", value=f"Date: {game[3]} | Teams: {game[4]} vs {game[5]}", inline=False)

    await ctx.send(embed=embed)

#website command
@bot.command()
async def website(ctx):
    embed = discord.Embed(title="Website", description="Visit the website for more information and to request membership to teams.", color=discord.Color.blue())
    embed.add_field(name="Link", value="https://vailminorleague.pythonanywhere.com", inline=False)
    await ctx.send(embed=embed)


# ADMIN COMMANDS


#make game command
@bot.command()
async def makegame(ctx, *, args):
    #ensure the command is run by an admin
    if not discord.utils.get(ctx.author.roles, name="admin"):
        await ctx.send("You do not have permission to use this command.")
    else:
        # validate the input
        if " v " not in args:
            await ctx.send("Invalid format. Use `!makegame Team1 v Team2`.")
            return
        else:
            # split the arguments into team names
            args = args.split(" v ")
            # find where to insert the new game
            gameAmount = int(sheet.cell(19, 1).value)
            rangeString = f"A{str(gameAmount + 21)}:F{str(gameAmount + 21)}"
            # find next id to use
            latestId = int(sheet.cell(19, 2).value)
            #store game
            sheet.update([[args[0], args[1], "-", "-", "-", str(latestId + 1)]], rangeString)
            # increment game count and latest id
            sheet.update_cell(19, 1, str(gameAmount + 1))
            sheet.update_cell(19, 2, str(int(latestId) + 1))
            # send confirmation message
            await ctx.send(f"Game created between **{args[0]}** and **{args[1]}**. ID: {latestId + 1}")
            # notify captains
            await notifyCaptains(args[0], args[1], latestId + 1)

async def notifyCaptains(homeTeam, awayTeam, gameId):

    # get the roles needed
    guild = bot.guilds[0]
    homeCaptainRole = discord.utils.get(guild.roles, name=f"{homeTeam} Captain")
    awayCaptainRole = discord.utils.get(guild.roles, name=f"{awayTeam} Captain")

    # contstruct the message
    embed = discord.Embed(title="New Game Scheduled", color=discord.Color.green())
    embed.add_field(name="Home Team", value=homeTeam, inline=True)
    embed.add_field(name="Away Team", value=awayTeam, inline=True)  
    embed.add_field(name="Game ID", value=gameId, inline=True)
    embed.set_footer(text="Please use #teamcaptains to discuss a time and then use !setdatetime ID DD-MM-YYYY_HH:MM to set the datetime for the game. You can also use !setteam ID PLAYER1, PLAYER2, PLAYER3 to set the team you want to play with.")

    errorNames = []
    # Notify all members with the respective captain role
    for member in guild.members:
        if homeCaptainRole in member.roles or awayCaptainRole in member.roles:
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                errorNames.append(member.display_name)
    for channel in guild.text_channels:
                    if channel.name == "teamcaptains":
                        await channel.send(embed=embed)
                        for name in errorNames:
                             await channel.send(f"Could not DM {member.display_name}, please check your DMs.")


# CAPTAIN COMMANDS


# Command to set the time for a game
@bot.command()
async def setdatetime(ctx, id: int, datetime: str):
    # find teams involved in the game
    (home, away) = findTeamsFromGame(id)
    if not home or not away:
        await ctx.send(f"No game found with ID {id}. Please check the ID and try again.")
        return
    print(f"Setting datetime for game {id} between {home} and {away}")
    # Ensure the command is run by an admin
    if not(discord.utils.get(ctx.author.roles, name=f"{home} Captain") or discord.utils.get(ctx.author.roles, name=f"{away} Captain")):
        await ctx.send("You do not have permission to use this command.")
        return
    datetime = datetime.strip() # clean data a bit
    # Validate the time format (DD-MM-YYYY_HH:MM)
    try:
        date, time = datetime.split("_")
        print("0")
        # a bunch of validation
        if len(str(date)) != 10 or len(str(time)) != 5 or not(date[2] == '-' and date[5] == '-' and time[2] == ':' and date[:2].isdigit() and date[3:5].isdigit() and date[6:10].isdigit() and time[:2].isdigit() and time[3:].isdigit()):
            print("1")
            raise ValueError("Invalid time format")
        # a bunch more validation
        else:
            #validate date and time components
            day, month, year = map(int, date.split("-"))
            hour, minute = map(int, time.split(":"))
            if not (1 <= day <= 31 and 1 <= month <= 12 and 0 <= hour < 24 and 0 <= minute < 60): # cant be bothered to do specific month lengths
                print("2")
                raise ValueError("Invalid date or time values")
            else:
                # get confirmation from other captain
                otherTeam = home if any(role.name == f"{away} Captain" for role in ctx.author.roles) else away
                roleName = f"{otherTeam} Captain"
                otherCaptainRole = discord.utils.get(ctx.guild.roles, name=roleName)
                adminRole = discord.utils.get(ctx.guild.roles, name="admin")
                message = await ctx.send(f"Game datetime set to {datetime} by {ctx.author.mention} for game ID {id}. Please confirm this with a **✅ reaction** or deny it with a **❌ reaction** {otherCaptainRole.mention}")
                # check for reaction
                confirmEmoji = "✅"
                denyEmoji = "❌"
                await message.add_reaction(confirmEmoji)
                await message.add_reaction(denyEmoji)

                def check(reaction, user):
                    print(f"Reaction: {reaction.emoji}, User: {user}")
                    return (
                        user != bot.user and
                        str(reaction.emoji) in [confirmEmoji, denyEmoji] and
                        reaction.message.id == message.id
                    )

                confirmed = False
                while not confirmed:
                    try:
                        if not confirmed:
                            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                            guild = bot.guilds[0]
                            member = guild.get_member(user.id)
                            if member and (otherCaptainRole in member.roles or adminRole in member.roles):
                                if str(reaction.emoji) == denyEmoji:
                                    await ctx.send(f"Game time denied by {member.mention}. Please use !setdatetime again to set the datetime.")
                                    return
                                elif str(reaction.emoji) == confirmEmoji:
                                    # confirmation received
                                    print(f"Confirmation received from {member.display_name}")
                                    confirmed = True
                                    await ctx.send(f"Game time confirmed by {member.mention} at {datetime}.")
                                    # Update the game time in the sheet
                                    gameAmount = int(sheet.cell(19, 1).value)
                                    games = sheet.get_values(f"A21:F{21 + gameAmount}")
                                    for game in games:
                                        if game[5] == str(id):
                                            # update the game time
                                            sheet.update_cell(21 + games.index(game), 3, datetime)
                                            await ctx.send(f"Game time for ID {id} updated to {datetime}.")
                                            return
                            # game confirmed
                    except asyncio.TimeoutError:
                        await ctx.send(f" No confirmation received, {otherCaptainRole.mention}, please confirm.")
    except ValueError:
        await ctx.send("Invalid time format. Use DD-MM-YYYY HH:MM (24-hour format).")
        print(ValueError)
        return

    
                        
     
# Command to set the team for a game
@bot.command()
async def setteam(ctx, id: int, *, players: str):
    # Ensure the command is run by a captain of the team
    if not(discord.utils.get(ctx.author.roles, name=f"{findTeamsFromGame(id)[0]} Captain") or discord.utils.get(ctx.author.roles, name=f"{findTeamsFromGame(id)[1]} Captain")):
        await ctx.send("You do not have permission to use this command.")
        return

    # validate id
    try:
        (home, away) = findTeamsFromGame(id)
    except TypeError:
        await ctx.send(f"No game found with ID {id}. Please check the ID and try again.")
        return

    # Validate the input and clean it a bit
    players = players.strip()
    if not players:
        await ctx.send("Please provide a list of players, seperated by commas.")
        return
    
    # check which team and hence column to update
    column = 4 if any(role.name == f"{home} Captain" for role in ctx.author.roles) else 5

    # Split the players by comma and strip whitespace
    playerList = [player.strip() for player in players.split(",")]
    playerList = [player for player in playerList if player] 
    players = ", ".join(playerList)

    # Find the game in the sheet
    games = getUpcomingGames("")
    
    for i, game in enumerate(games, start=1):
        if game[5] == str(id):
            # Update the team in the sheet
            sheet.update_cell(20 + i, column, players)
            await ctx.send(f"Team for game ID {id} set to: {players}")
            return
    
    # no game found with that id
    await ctx.send(f"No game found with ID {id}.")

# Command to give in results of a game
@bot.command()
async def result(ctx, id: int, game1: str, game2: str, game3: str):
    try:
        (home, away) = findTeamsFromGame(id)
    except:
        await ctx.send(f"No game found with ID {id}. Please check the ID and try again.")
        return
    if not(discord.utils.get(ctx.author.roles, name=f"{home} Captain") or discord.utils.get(ctx.author.roles, name=f"{away} Captain") or discord.utils.get(ctx.author.roles, name=f"admin")):
        await ctx.send("You do not have permission to use this command.")
        return
    
    #requires authorization if not an admin
    authorized = True if discord.utils.get(ctx.author.roles, name="admin") else False

    # Validate the input and clean it a bit
    valid = True
    for game in [game1.strip(), game2.strip(), game3.strip()]:
        if not(game[0].isdigit() and game[2].isdigit() and game[1] == ":") or not(0 <= int(game[0]) <= 9 and 0 <= int(game[2]) <= 9): 
            valid = False
            break
    if not valid:
        await ctx.send("Invalid format. Use `!result ID Game1 Game2 Game3` where each game is in the format `X:Y` (e.g. `1:0`).")
        return
    elif not authorized:
        otherTeam = home if any(role.name == f"{away} Captain" for role in ctx.author.roles) else away
        roleName = f"{otherTeam} Captain"
        otherCaptainRole = discord.utils.get(ctx.guild.roles, name=roleName)
        adminRole = discord.utils.get(ctx.guild.roles, name="admin")
        message = await ctx.send(f"Scores set as {game1} | {game2} | {game3} by {ctx.author.mention} for game ID {id}. Please confirm this with a **reaction** {otherCaptainRole.mention}")
        # check for reaction
        confirmEmoji = "✅"
        denyEmoji = "❌"

        await message.add_reaction(confirmEmoji)
        await message.add_reaction(denyEmoji)

        def check(reaction, user):
            print(f"Reaction: {reaction.emoji}, User: {user}")
            return (
                user != bot.user and
                str(reaction.emoji) in [confirmEmoji, denyEmoji] and
                reaction.message.id == message.id
            )
        
        # continuously try until confirmed
        confirmed = False
        while not confirmed:
            try:
                if not confirmed:
                    reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                    guild = bot.guilds[0]
                    member = guild.get_member(user.id)
                    # make sure captain or admin
                    if member and (otherCaptainRole in member.roles or adminRole in member.roles):
                        if str(reaction.emoji) == denyEmoji:
                            await ctx.send(f"Game score denied by {member.mention}. Please use !result again to set the scores.")
                            return
                        elif str(reaction.emoji) == confirmEmoji:
                            print(f"Confirmation received from {member.display_name}")
                            confirmed = True
                            await ctx.send(f"Game score confirmed by {member.mention} as {game1}, {game2}, {game3}.")
                            if await setresults(id, game1, game2, game3):
                                await ctx.send(f"Game score set as {game1}, {game2}, {game3} for game ID {id} by {ctx.author.mention}.")
                                await standings(ctx)
                            else:
                                await ctx.send(f"Error setting game score for ID {id}.")
                            if await moveToFinishedGames(id, game1, game2, game3):
                                await ctx.send(f"Game with ID {id} moved to finished games.")
                            else:
                                await ctx.send(f"Error moving game with ID {id} to finished games.")
                                return
            except asyncio.TimeoutError:
                        await ctx.send(f" No confirmation received, {otherCaptainRole.mention}, please confirm.")
    elif authorized:
        await ctx.send(f"Game score set as {game1}, {game2}, {game3} for game ID {id} by {ctx.author.mention}.")
        if await setresults(id, game1, game2, game3):
            await ctx.send(f"Game score set as {game1}, {game2}, {game3} for game ID {id} by {ctx.author.mention}.")
            await standings(ctx)
        else:
            await ctx.send(f"Error setting game score for ID {id}.")
        if await moveToFinishedGames(id, game1, game2, game3):
            await ctx.send(f"Game with ID {id} moved to finished games.")
            return
        else:
            await ctx.send(f"Error moving game with ID {id} to finished games.")
            return

# set results into sheet and update standings
async def setresults(id, game1, game2, game3):
    try:
        # get teams to update their stats
        (home, away) = findTeamsFromGame(id)
        # get standings
        standings = getStandings()  
        # find home and away teams in standings

        homeTeam = []
        awayTeam = []

        for team in standings:
            if team[0] == home:
                for item in team:
                    if item.isdigit():
                        # convert to int and store in homeTeam
                        homeTeam.append(int(item))
                    else:
                        homeTeam.append(item)
            elif team[0] == away:
                for item in team:
                    if item.isdigit():
                        # convert to int and store in homeTeam
                        awayTeam.append(int(item))
                    else:
                        awayTeam.append(item)
        # update points
        games = [game1, game2, game3]
        for game in games:
            homeTeam[1] += int(game[0])
            awayTeam[1] += int(game[2])
        # update map wins (and count map wins for match wins)
        homeTeamMapWins = 0
        awayTeamMapWins = 0
        for game in games:
            if int(game[0]) > int(game[2]):
                homeTeam[2] += 1
                homeTeamMapWins += 1
            elif int(game[0]) < int(game[2]):
                awayTeam[2] += 1
                awayTeamMapWins += 1
            else:
                # shoot out an error message to standings channel because i dont want to pass ctx
                guild = bot.guilds[0]
                for channel in guild.text_channels:
                    if channel.name == "standings":
                        await channel.send("big ole error, map wins are equal, this should not happen")
        # update match wins
        if homeTeamMapWins > awayTeamMapWins:
            homeTeam[3] += 1
        else:
            awayTeam[3] += 1
        # update mmr
        homeTeam[4] = homeTeam[1] + (homeTeam[2] * 2) + (homeTeam[3] * 10)
        awayTeam[4] = awayTeam[1] + (awayTeam[2] * 2) + (awayTeam[3] * 10)
        # update standings in sheet
        for i, team in enumerate(standings, start=1):
            if team[0] == home:
                sheet.update_cell(1 + i, 2, str(homeTeam[1]))
                sheet.update_cell(1 + i, 3, str(homeTeam[2]))
                sheet.update_cell(1 + i, 4, str(homeTeam[3]))
                sheet.update_cell(1 + i, 5, str(homeTeam[4]))
            elif team[0] == away:
                sheet.update_cell(1 + i, 2, str(awayTeam[1]))
                sheet.update_cell(1 + i, 3, str(awayTeam[2]))
                sheet.update_cell(1 + i, 4, str(awayTeam[3]))
                sheet.update_cell(1 + i, 5, str(awayTeam[4]))
            return True
    except Exception as e:
        print(e)
        return False

# move teams to the finished games section
async def moveToFinishedGames(id, game1, game2, game3):
    # find next spot in the finished games section
    finishedGamesNumber = int(sheet.cell(48, 2).value)
    # find the game in the sheet
    gameAmount = int(sheet.cell(19, 1).value)
    games = sheet.get_values(f"A21:F{21 + gameAmount}")
    for i, game in enumerate(games):
        if game[5] == str(id):
            # move the game to the finished games section
            finishedGamesRange = f"A{50 + finishedGamesNumber}:I{50 + gameAmount}"
            game = [game[0], game[1], game[2], game[3], game[4], game[5], game1, game2, game3]
            sheet.update([game], finishedGamesRange)
            # remove the game from the upcoming games section
            for index in range(i, gameAmount):
                next_game = sheet.row_values(21 + index + 1)
                sheet.update([next_game], f"A{21 + index}:F{21 + index}")
            # clear the game in the upcoming games section
            sheet.update([["", "", "", "", "", ""]], f"A{21 + gameAmount}:F{20 + gameAmount}")
            # increment the finished games number
            sheet.update_cell(48, 2, str(finishedGamesNumber + 1))
            # update the game amount
            sheet.update_cell(19, 1, str(gameAmount - 1))
            return True
    return False



    

            






# Event to send standings when the bot is ready
@bot.event
async def on_ready():
    if not bot.guilds:
        print("No guilds found")
        return
    else:
        guild = bot.guilds[0]
        for channel in guild.text_channels:
            if channel.name == "standings":
                embed = formatStandings()
                print("running")
                await channel.send(embed=embed)
                return
        
        # check events
        bot.loop.create_task(checkEvents())

# Async tasks for bot and server
async def start_web():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 5000)
    await site.start()
    print("Web server running...")

async def main():
    await asyncio.gather(
        start_web(),
        # Run Discord bot
        runBot()
    )

async def runBot():
    botToken = os.getenv("botToken")
    print("Starting Discord bot")
    await bot.start(botToken)

# Run bot and Flask app
if __name__ == "__main__":
    ## Start Flask app in a separate thread
    #flaskThread = Thread(target=runFlask)
    #flaskThread.start()
#
    ## Run Discord bot
    #botToken = os.getenv("botToken")
    #print("Starting Discord bot")
    #bot.run(botToken)

    # Run everything in one event loop
    asyncio.run(main())