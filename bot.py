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





@bot.event
async def on_ready():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == "standings":
                standings = getStandings()
                embed = discord.Embed(title="Current Standings", color=discord.Color.blue())
                count = 0
                embed.add_field(name="Place | Name | Points | Map wins | Match wins | MMR | Captain", inline=False)
                for team in standings:
                    count += 1
                    embed.add_field(name=f"{count} | **{team[0]}** | {team[1]} | {team[2]} | {team[3]} | {team[4]} | {team[5]}", inline=True)

                await channel.send(embed=embed)

#run bot
if __name__ == "__main__":
    with open("keys/botToken.txt", "r") as token_file:
        bot_token = token_file.read().strip()
    bot.run(bot_token)