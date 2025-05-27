import discord
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app import getStandings

# Setup Discord bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
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
    embed.set_footer(text="Please use #teamcaptains to discuss a time and then use !settime to set the time for the game. You can also use !setteam ID PLAYER1, PLAYER2, PLAYER3 to set the team you want to play with.")
    embed.set_thumbnail(url=guild.icon.url)

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
                        
                    

# Event to send standings when the bot is ready
@bot.event
async def on_ready():
    guild = bot.guilds[0]
    for channel in guild.text_channels:
        if channel.name == "standings":
            embed = formatStandings()
            print("running")
            await channel.send(embed=embed)
            break

#run bot
if __name__ == "__main__":
    with open("keys/botToken.txt", "r") as token_file:
        bot_token = token_file.read().strip()
    bot.run(bot_token)