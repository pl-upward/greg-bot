import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='g~', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        await message.reply("sss")

    await bot.process_commands(message)

@bot.command(name='pet')
async def pet(ctx):
    await ctx.message.add_reaction("❤️")

bot.run(TOKEN)