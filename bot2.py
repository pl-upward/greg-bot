#!/usr/bin/env python

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from openai import OpenAI
import random
from collections import defaultdict, deque

# initialize dotenv and connect
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = OpenAI()

# discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='G!', intents=intents)

# Keep track of x most recent message objects
# Key: channel ID, Value: deque of messages
channel_messages = defaultdict(lambda: deque(maxlen=20))

# Set up config file on server join
SERVER_CONFIG_DIR = "server_configs"


# Set up default fields
def load_config(path):
    with open(path, "r") as f:
        return json.load(f)


default_config = load_config("default_config.json")


# Load a server's config
def load_server_config(guild_id):
    path = os.path.join(SERVER_CONFIG_DIR, f"{guild_id}.json")
    if os.path.exists(path):
        return load_config(path)
    return {}


# Log a new user in the guild's json
def add_new_user(user_id, guild_id, name, summary="", approval_rating=5.0):
    file_path = f"{SERVER_CONFIG_DIR}/{guild_id}.json"

    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist.\n")
        return

    config = load_config(file_path)

    config.setdefault("users", {})
    config["users"][str(user_id)] = {
        "name": name,
        "summary": summary,
        "approval_rating": approval_rating
    }

    with open(file_path, "w") as f:
        json.dump(config, f, indent=4)


########################################################################################################################
# <editor-fold desc="whitelist check">
# Checks if user is in the server's whitelist
@bot.check
def is_whitelisted(ctx):
    guild_id = str(ctx.guild.id)
    config_path = f"{SERVER_CONFIG_DIR}/{guild_id}.json"

    if not os.path.exists(config_path):
        print(f"Error: {config_path} does not exist.\n")
        return False

    config = load_config(config_path)

    whitelist = config.get("whitelist", [])
    return ctx.author.id in whitelist
# </editor-fold>


# <editor-fold desc="logs that bot is ready">
# Log that the bot is working to console
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
# </editor-fold>


# <editor-fold desc="join/leave cmds">
# Create config for each server the bot is in
@bot.event
async def on_guild_join(guild):
    os.makedirs(SERVER_CONFIG_DIR, exist_ok=True)
    config_path = os.path.join(SERVER_CONFIG_DIR, f"{guild.id}.json")

    if not os.path.exists(config_path):
        default_config_json = load_config("default_config.json")
        default_configs = {
            "prefix": default_config_json.get("prefix", "G!"),
            "model": default_config_json.get("model", "gpt-4.1-nano"),
            "system_prompt": default_config_json.get("system_prompt", ""),
            "temperature": default_config_json.get("temperature", 0),
            "whitelist": default_config_json.get("whitelist", []),
            "response_chance": default_config_json.get("response_chance", 0),
            "channel_msg_buffer": default_config_json.get("channel_msg_buffer", 20),
            "users": default_config_json.get("users", {})
        }

        with open(config_path, "w") as f:
            json.dump(default_configs, f, indent=4)

        print(f"Created config for guild {guild.name} ({guild.id})")


# Remove config when bot has left server - I DON'T THINK THIS WORKS
@bot.event
async def on_guild_remove(guild):
    config_path = f"configs/{guild.id}.json"
    try:
        if os.path.exists(config_path):
            os.remove(config_path)
            print(f"Removed config for guild {guild.name} ({guild.id})")
    except Exception as e:
        print(f"Failed to remove config for guild {guild.name} ({guild.id})")
# </editor-fold>


# <editor-fold desc="testing cmds">
@bot.command(name="add_me")
async def add_user(ctx, summary: str, rating: float):
    user_id = ctx.author.id
    guild_id = ctx.guild.id
    username = ctx.author.display_name

    add_new_user(user_id, guild_id, username, summary, rating)

    await ctx.send(f"Added {username} to {guild_id} with summary '{summary}' and rating {rating}")

# </editor-fold>
########################################################################################################################

bot.run(TOKEN)
