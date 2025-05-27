import discord
from discord.ext import commands
import gspread
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
from app import getStandings

# Setup Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True
intents.reactions = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Setup Google Sheets access
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("keys/key.json", scope)
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
        embed.add_field(name=f"{count} | **{team[0]}** | {team[1]} Points| {team[2]} Map wins | {team[3]} Match wins | {team[4]} MMR", value="", inline=True)
    return embed

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




# Command to set the time for a game
@bot.command()
async def setdatetime(ctx, id: int, datetime: str):
    # find teams involved in the game
    (home, away) = findTeamsFromGame(id)
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
                message = await ctx.send(f"Game datetime set to {datetime} by {ctx.author.mention} for game ID {id}. Please confirm this with a **reaction** {otherCaptainRole.mention}")
                # check for reaction
                emoji = "✅"
                await message.add_reaction(emoji)

                def check(reaction, user):
                    print(f"Reaction: {reaction.emoji}, User: {user}")
                    return (
                        user != bot.user and
                        str(reaction.emoji) == emoji and
                        reaction.message.id == message.id
                    )

                confirmed = False
                while not confirmed:
                    try:
                        if not confirmed:
                            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                            guild = bot.guilds[0]
                            member = guild.get_member(user.id)
                            if member and otherCaptainRole in member.roles:
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
                                        break
                            else:
                                pass
                            # game confirmed
                    except asyncio.TimeoutError:
                        await ctx.send(" No confirmation received, use !setdatetime again to set the datetime.")

            
        
    except ValueError:
        await ctx.send("Invalid time format. Use DD-MM-YYYY HH:MM (24-hour format).")
        print(ValueError)
        return

    
                        
def findTeamsFromGame(id):
    # find from only the games part of the sheet
    gameAmount = int(sheet.cell(19, 1).value)
    games = sheet.get_values(f"A21:F{21 + gameAmount}")
    for game in games:
        if game[5] == str(id):
            return game[0], game[1]
    
     

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

#run bot
if __name__ == "__main__":
    with open("keys/botToken.txt", "r") as tokenFile:
        botToken = tokenFile.read().strip()
    print("Starting")
    bot.run(botToken)
