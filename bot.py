import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from openai import OpenAI
import re

# load env vars and openai setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = OpenAI()

# load json
with open("greg_config.json", "r") as f:
    config = json.load(f)

WHITELIST = config.get("whitelist", [])
SYSTEM_PROMPT = config.get("system_prompt", "")
MAX_TOKENS = config.get("max_tokens", 1024)
TEMPERATURE = config.get("temperature", 1.0)
MODEL = config.get("model", "gpt-4.1-nano")

# discord bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='g~', intents=intents)


# bot is working
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def replace_mentions_with_usernames(message: discord.Message, text: str) -> str:
    pattern = r"<@!?(\d+)>"
    matches = re.findall(pattern, text)

    for user_id in matches:
        try:
            user = await message.guild.fetch_member(user_id)
            username = user.display_name
            text = re.sub(f"<@!?{user_id}>", username, text)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue

    return text


# reply to mentions
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user in message.mentions:
        if message.author.id not in WHITELIST:
            await message.reply("sss (You are not whitelisted to talk to Greg. Ask Garrett or Erin for access!)")
            return

        async with message.channel.typing():
            try:
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
                                    "text": message.content
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

                reply = response.output[0].content[0].text

                await message.reply(reply[:2000])

            except Exception as e:
                await message.reply(f"Error: {e}")

    await bot.process_commands(message)


@bot.command(name='askgreg')
async def ask_greg(ctx, *, prompt: str):
    async with ctx.typing():
        try:
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
                text={
                    "format": {
                        "type": "text"
                    }
                },
                reasoning={},
                tools=[],
                temperature=TEMPERATURE,
                max_output_tokens=MAX_TOKENS,
                top_p=1,
                store=True
            )

            reply = response.output[0].content[0].text

            await ctx.reply(reply[:2000])
        except Exception as e:
            await ctx.reply(f'Error: {e}')


# pet the snek
@bot.command(name='pet')
async def pet(ctx):
    await ctx.message.add_reaction("❤️")


# only let whitelisted users use him
@bot.check
def is_whitelisted(ctx):
    return ctx.author.id in WHITELIST


bot.run(TOKEN)