#!/usr/bin/env python

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from openai import OpenAI
import random
from collections import defaultdict, deque

# <editor-fold desc="bot setup">
# initialize dotenv and connect
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = OpenAI()

# discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='G!', intents=intents)

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
# </editor-fold>


# Log a new user in the guild's json
def update_user(user_id, guild_id, name, summary="Greg doesn't know this person yet.", approval_rating=5.0):
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


# Remove the user from the json
def remove_user(user_id, guild_id):
    file_path = f"{SERVER_CONFIG_DIR}/{guild_id}.json"

    if not os.path.exists(file_path):
        print(f"Error: {file_path} does not exist.\n")
        return

    config = load_config(file_path)
    users = config.get("users", {})
    user_id_str = str(user_id)

    if user_id_str in users:
        del users[user_id_str]
        config["users"] = users

        with open(file_path, "w") as f:
            json.dump(config, f, indent=4)

        print(f"User {user_id_str} removed.\n")
    else:
        print(f"User {user_id_str} does not exist.\n")


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


# <editor-fold desc="modify users">
@bot.command(name="remove")
async def remove(ctx, member: discord.Member):
    guild_id = ctx.guild.id
    user_id = member.id

    remove_user(user_id, guild_id)
    await ctx.send(f"*Greg's memories of {member.display_name} are fading...*")


@bot.command(name="edit")
async def edit(ctx, member: discord.Member, rating: float, *, summary: str):
    guild_id = ctx.guild.id
    user_id = member.id
    name = member.display_name

    update_user(user_id, guild_id, name, summary, rating)
    await ctx.send(f"*Greg seems to think differently of {name} after hearing this new information.*")


# </editor-fold>


# <editor-fold desc="IMPORTANT AI COMMANDS">
async def get_response(prompt: str, guild_id: int) -> str:
    config_path = os.path.join(SERVER_CONFIG_DIR, f"{guild_id}.json")

    if not os.path.exists(config_path):
        print(f"Error: Config not found for guild {guild_id}")

    config = load_config(config_path)

    model = config.get("model", "gpt-4.1-nano")
    system_prompt = config.get("system_prompt", "")
    temperature = config.get("temperature", 0.8)
    max_tokens = config.get("max_output_tokens", 2048)

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_prompt
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        }
                    ]
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[],
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=1,
            store=False
        )

        output_text = response.output[0].content[0].text.strip()
        if output_text.lower() in ["something went wrong.", "an error occured."]:
            return "*Greg slithers under a rock, disappearing into the darkness.* (You scared him)"

    except Exception as e:
        print(f"Error: Greg failed to create a response. {e}")
        return "*Greg slithers under a rock, disappearing into the darkness.* (OpenAI encountered an error)"
# </editor-fold>


# <editor-fold desc="Message handling">


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = message.guild.id
    file_path = f"{SERVER_CONFIG_DIR}/{guild_id}.json"

    if not os.path.exists(file_path):
        print(f"Error: no config for server {guild_id}")
        return

    config = load_config(file_path)

    response_chance = config.get("response_chance", 0)
    msg_content = message.content.lower()

    if "greg" in msg_content or random.random() < response_chance:
        async with message.channel.typing():
            try:
                reply = await get_response(message.content, message.guild.id)
                await message.reply(reply[:2000])
            except Exception as e:
                await message.reply("*Greg slithers under a rock, disappearing into the darkness.* (OpenAI failed to "
                                    "get a response)")
        return

    if bot.user in message.mentions:
        if not is_whitelisted(message.author.id):
            # YOU GOTTA REDO THIS WHOLE THING BRUH
            return

    await bot.process_commands(message)
# </editor-fold>


# <editor-fold desc="silly cmds">


# </editor-fold>
########################################################################################################################

bot.run(TOKEN)
