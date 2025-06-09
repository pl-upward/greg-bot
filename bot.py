#!/usr/bin/env python
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from openai import OpenAI
import shutil
import random

# load discord token and openai client
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = OpenAI()

# bot needs message intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='G!', intents=intents)

SERVER_CONFIG_DIR = "server_configs"
DEFAULT_CONFIG_PATH = "default_config.json"


# returns json object :D
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# writes to json :D
def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_config_path(guild_id):
    return os.path.join(SERVER_CONFIG_DIR, f"{guild_id}.json")


default_config = load_json(DEFAULT_CONFIG_PATH)


def load_server_config(guild_id):
    path = os.path.join(SERVER_CONFIG_DIR, f"{guild_id}.json")
    if not os.path.exists(path):
        shutil.copy(DEFAULT_CONFIG_PATH, path)
    return load_json(path)


# THIS FUNCTION DOES LIKE EVERYTHING FOR COMMANDS
# Input Variables:
# ctx - message object to read from
# field - json variable to change
# data - data to change it to
# append - append to a list. only use on lists
# remove - remove from a list. only use on lists
# Returns:
# True or False depending on status
async def change_json(ctx, field, data, expensive, append=False, remove=False):
    path = get_config_path(ctx.guild.id)
    config = load_json(path)

    is_whitelisted = ctx.author.id in config.get("super_whitelist", [])
    is_admin = ctx.author.guild_permissions.administrator

    if not is_whitelisted and (not is_admin or expensive):
        await ctx.reply("*You don't have permission to run this command.*")
        return False

    if field not in config:
        await ctx.reply(f"*Field {field} not found in config.*")
        return False

    if append or remove:
        if not isinstance(config[field], list):
            print(f"[Warning] Tried to append or remove to a non-list variable.\n")
            return False
        if data in config[field] and append:
            await ctx.reply(f"*Field {field} is already in {data}.*")
            return False
        if append:
            config[field].append(data)
            save_json(path, config)
            await ctx.reply(f"*Added {data} to {field}.*")
        if remove:
            config[field].remove(data)
            save_json(path, config)
            await ctx.reply(f"*Removed {data} from {field}.*")
        return True

    config[field] = data
    save_json(path, config)
    await ctx.reply(f"*Set {field} to {data}.*")
    return True


async def format_reply_content(msg, name_model):
    content = msg.content
    if msg.reference:
        try:
            replied_to = await msg.channel.fetch_message(msg.reference.message_id)
            content = (f"(In reply to {replied_to.author.display_name}: \"{replied_to.content}\")\n"
                       f"{msg.author.display_name}: {content}")
        except discord.NotFound:
            pass
    elif not name_model:
        content = f"{msg.author.display_name}: {content}"
    return content


@bot.event
async def on_guild_join(guild):
    load_server_config(guild.id)


# <editor-fold desc="OH GOD THERES SO MANY SETTERS">
@bot.command(name="setmodel")
async def set_model(ctx, *, model: str):
    await change_json(ctx, "model", model, True)


@bot.command(name="setprompt")
async def set_prompt(ctx, *, new_prompt: str):
    await change_json(ctx, "system_prompt", new_prompt, False)


@bot.command(name="settemperature")
async def set_temperature(ctx, *, temperature: float):
    if 0.0 <= temperature <= 2.0:
        await change_json(ctx, "temperature", temperature, False)
    else:
        await ctx.reply(f"{temperature} is an invalid number. Please pick a number between 0 and 2.0.")


@bot.command(name="addsuperadmin")
async def add_super_admin(ctx, *, userid: int):
    await change_json(ctx, "super_whitelist", userid, True, True)


@bot.command(name="removesuperadmin")
async def remove_super_admin(ctx, *, userid: int):
    await change_json(ctx, "super_whitelist", userid, True, False, True)


@bot.command(name="adduser")
async def add_user(ctx, *, userid: int):
    await change_json(ctx, "user_whitelist", userid, True, True)


@bot.command(name="removeuser")
async def remove_user(ctx, *, userid: int):
    await change_json(ctx, "user_whitelist", userid, True, False, True)


@bot.command(name="setresponsechance")
async def set_chance(ctx, *, chance: float):
    await change_json(ctx, "response_chance", chance, True)


@bot.command(name="setchannelbuffer")
async def set_buffer_size(ctx, *, amount: int):
    await change_json(ctx, "channel_message_buffer", amount, True)


@bot.command(name="addchannel")
async def add_conversation_channel(ctx):
    await change_json(ctx, "conversation_channels", ctx.channel.id, False, True)


@bot.command(name="removechannel")
async def remove_conversation_channel(ctx):
    await change_json(ctx, "conversation_channels", ctx.channel.id, False, False, True)


@bot.command(name="wipeconfig")
async def wipe_config(ctx):
    path = get_config_path(ctx.guild.id)
    config = load_json(path)

    is_whitelisted = ctx.author.id in config.get("super_whitelist", [])
    is_admin = ctx.author.guild_permissions.administrator

    if not (is_whitelisted or is_admin):
        await ctx.reply("*You don't have permission to wipe the config file.*")
        return

    if os.path.exists(path):
        os.remove(path)
        await ctx.reply("goodbye bro")
    else:
        return


@bot.command(name="dumpconfig")
async def dump_config(ctx):
    path = get_config_path(ctx.guild.id)
    if not os.path.exists(path):
        await ctx.reply("Config file does not exist for this server.")
        return

    config = load_json(path)

    # Optional: restrict to admins or super whitelist
    is_whitelisted = ctx.author.id in config.get("super_whitelist", [])
    is_admin = ctx.author.guild_permissions.administrator

    if not (is_whitelisted or is_admin):
        await ctx.reply("*You don't have permission to view the config.*")
        return

    # Format nicely for Discord (limit if too long)
    pretty_config = json.dumps(config, indent=2)
    if len(pretty_config) > 1900:
        await ctx.reply("*Config is too large to display in Discord.*")
        return

    await ctx.reply(f"```json\n{pretty_config}\n```")

# </editor-fold>

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")


# This is the main on_message command
@bot.event
async def on_message(ctx):
    if ctx.author.bot:
        return

    # </editor-fold>
    config = load_server_config(ctx.guild.id)
    if ctx.content.startswith("G!"):
        await bot.process_commands(ctx)
        return
    system_prompt = config.get("system_prompt", "")
    response_chance = config.get("response_chance", 0)
    user_whitelist = config.get("user_whitelist", [])
    model = config.get("model", "gpt-4o-mini")
    message_limit = config.get("channel_message_buffer", 20)
    conversation_channels = config.get("conversation_channels", [])
    name_models = config.get("name_models", ["gpt-4o", "gpt-4o-mini"])

    chance_hit = not (random.random() > response_chance)
    name_in_msg = ctx.guild.me.display_name.casefold() in ctx.content.casefold()
    if not (chance_hit or name_in_msg):
        return
    if ctx.channel.id not in conversation_channels:
        return
    if ctx.author.id not in user_whitelist:
        return

    async with ctx.channel.typing():
        messages = [msg async for msg in ctx.channel.history(limit=message_limit)]
        messages.reverse()

        conversation = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        for msg in messages:
            role = "assistant" if msg.author.id == bot.user.id else "user"
            name_model = model in name_models
            content = await format_reply_content(msg, name_model)

            message_entry = {
                "role": role,
                "content": content
            }

            if name_model:
                message_entry["name"] = msg.author.display_name

            conversation.append(message_entry)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=conversation
            )
        except Exception as e:
            print(f"OpenAI API error: {e}")
            print("Conversation: "+str(conversation))
            return

        reply_text = response.choices[0].message.content.strip()
        if reply_text:
            await ctx.reply(reply_text, mention_author=True)
        return


bot.run(TOKEN)
