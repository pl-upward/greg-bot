import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from openai import OpenAI
import random

# Load env vars and OpenAI setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = OpenAI()


# Load config from JSON
def load_config():
    with open("greg_config.json", "r") as f:
        return json.load(f)


config = load_config()

WHITELIST = config.get("whitelist", [])
SYSTEM_PROMPT = config.get("system_prompt", "")
MAX_TOKENS = config.get("max_tokens", 1024)
TEMPERATURE = config.get("temperature", 1.0)
MODEL = config.get("model", "gpt-4.1-nano")
RESPONSE_CHANCE = config.get("response_chance", 0)

# Discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='G!', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def get_greg_response(prompt: str) -> str:
    response = client.responses.create(
        model=MODEL,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": SYSTEM_PROMPT
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
        temperature=TEMPERATURE,
        max_output_tokens=MAX_TOKENS,
        top_p=1,
        store=True
    )
    return response.output[0].content[0].text


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # check if "greg" is mentioned and reply to the message or a .5% chance to reply
    if "greg" in message.content.lower() or random.random() < RESPONSE_CHANCE:
        async with message.channel.typing():
            try:
                reply = await get_greg_response(message.content)
                await message.reply(reply[:2000])
            except Exception as e:
                await message.reply(f"Error: {e}")
        return

    # reply to mentions of the bot
    if bot.user in message.mentions:
        if message.author.id not in WHITELIST:
            await message.reply("sss (You are not whitelisted to talk to Greg. Ask Garrett or Erin for access!)")
            return

        async with message.channel.typing():
            try:
                reply = await get_greg_response(message.content)
                await message.reply(reply[:2000])
            except Exception as e:
                await message.reply(f"Error: {e}")

    await bot.process_commands(message)


@bot.command(name='askgreg')
async def ask_greg(ctx, *, prompt: str):
    async with ctx.typing():
        try:
            reply = await get_greg_response(prompt)
            await ctx.reply(reply[:2000])
        except Exception as e:
            await ctx.reply(f'Error: {e}')


@bot.command(name='pet')
async def pet(ctx):
    await ctx.message.add_reaction("❤️")


@bot.command(name='feed')
async def feed(ctx, *, prompt: str):
    async with ctx.typing():
        try:
            reply = await get_greg_response(ctx.author.name + " tries to feed you a " + prompt + ". How does Greg respond?")
            await ctx.reply(reply[:2000])
        except Exception as e:
            await ctx.reply(f'Error: {e}')



@bot.check
def is_whitelisted(ctx):
    return ctx.author.id in WHITELIST


bot.run(TOKEN)