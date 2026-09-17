import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# إعداد تطبيق Flask الصغير للحفاظ على البوت شاعلاً
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعداد بوت الديسكورد
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def stock(ctx):
    await ctx.send("📦 Stock is currently active and managed successfully!")

# تشغيل السيرفر الوهمي أولاً ثم البوت
keep_alive()

# ضع هنا توكن البوت الخاص بك بين القوسين
TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable not set.")
