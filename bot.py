import os
import json
import asyncio
import random
import discord
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
import aiohttp
from datetime import datetime, timedelta

# إعداد سيرفر Flask للبقاء شاعلاً 24/7 على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class AutoStoreBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='+', intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully.")

bot = AutoStoreBot()
bot.remove_command('help')

ADAMC_BOT_ID = 1505622388975468684
MY_USER_ID = 1350403970132213812

WALLET_FILE = "wallet.json"
HISTORY_FILE = "history.json"
REFERRAL_FILE = "referrals.json"
DAILY_FILE = "daily.json"

LOGS_WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "PUT_YOUR_DISCORD_WEBHOOK_URL_HERE")

async def send_log_webhook(title, description, color=discord.Color.gold()):
    if not LOGS_WEBHOOK_URL or LOGS_WEBHOOK_URL == "PUT_YOUR_DISCORD_WEBHOOK_URL_HERE":
        return
    embed = {
        "title": f"⚡ {title}",
        "description": description,
        "color": color.value,
        "footer": {"text": "Rayo Store Elite System • 2026"},
        "timestamp": datetime.utcnow().isoformat()
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(LOGS_WEBHOOK_URL, json={"embeds": [embed]}) as resp:
                pass
        except Exception:
            pass

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_user_coins(user_id):
    wallet = load_json(WALLET_FILE)
    return wallet.get(str(user_id), 0)

def update_user_coins(user_id, amount):
    wallet = load_json(WALLET_FILE)
    current = wallet.get(str(user_id), 0)
    wallet[str(user_id)] = max(0, current + amount)
    save_json(WALLET_FILE, wallet)

def add_history(user_id, item_bought):
    history = load_json(HISTORY_FILE)
    uid = str(user_id)
    if uid not in history:
        history[uid] = []
    history[uid].append(item_bought)
    save_json(HISTORY_FILE, history)

def get_total_sales_count():
    history = load_json(HISTORY_FILE)
    return sum(len(items) for items in history.values())

def load_stock_lines():
    stock_file = "stock.txt"
    if not os.path.exists(stock_file):
        return []
    with open(stock_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def count_stock():
    return len(load_stock_lines())

def get_and_remove_stock():
    stock_file = "stock.txt"
    lines = load_stock_lines()
    if not lines:
        return None
    item = lines[0]
    with open(stock_file, "w", encoding="utf-8") as f:
        f.writelines([l + "\n" for l in lines[1:]])
    return item

def add_to_stock(item):
    with open("stock.txt", "a", encoding="utf-8") as f:
        f.write(item + "\n")

def clear_stock_file():
    with open("stock.txt", "w", encoding="utf-8") as f:
        f.write("")

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="الأوامر العامة", description="استعراض الأوامر المتاحة لكافة الأعضاء", emoji="🌐", value="public"),
            discord.SelectOption(label="أوامر الإدارة والتذاكر", description="الأوامر الخاصة بفتح التذاكر وإدارة المبيعات", emoji="🛡️", value="admin")
        ]
        super().__init__(placeholder="اختر تصنيف الأوامر لعرضها...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "public":
            embed = discord.Embed(
                title="🌐 | قائمة الأوامر العامة",
                description="الأوامر المتاحة لجميع أعضاء السيرفر:\n\n"
                            "• `/ticket` أو `+ticket` - فتح تذكرة شراء جديدة\n"
                            "• `/wallet` أو `+wallet` - فحص رصيدك من عملات المتجر\n"
                            "• `/history` أو `+history` - عرض سجل مشترياتك السابقة\n"
                            "• `/store-info` أو `+store-info` - إحصائيات المتجر وحالة المخزون\n"
                            "• `/daily` أو `+daily` - استلام مكافأتك اليومية المجانية",
                color=discord.Color.blue()
            )
        elif self.values[0] == "admin":
            embed = discord.Embed(
                title="🛡️ | أوامر الإدارة والتذاكر",
                description="الأوامر المخصصة لإدارة العمليات والمخزون:\n\n"
                            "• `/addstock` أو `+addstock` - إضافة يوزر للمخزون\n"
                            "• `/stock` أو `+stock` - عرض عدد اليوزرات الجاهزة للبيع\n"
                            "• `/clearstock` أو `+clearstock` - مسح وتفريغ الستوك",
                color=discord.Color.orange()
            )
        
        embed.set_footer(text="Rayo Store Elite System • استخدم الـ Prefix (+) أو Slash (/)")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💳 شحن العملات أوتوماتيكياً", style=discord.ButtonStyle.blurple, custom_id="deposit_btn", emoji="💎")
    async def deposit_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        price_per_coin = 800000
        embed = discord.Embed(
            title="💎 | نظام الشحن التلقائي الفخم",
            description=f"مرحباً بك في بوابة الشحن الرسمية للمتجر.\n\n"
                        f"📌 **التسعيرة:** كل **1 عملة متجر** بـ **800k** كريديت.\n"
                        f"⚙️ **طريقة الشحن عبر بوت Adamc:**\n"
                        f"```text\n#credit <@{MY_USER_ID}> [المبلغ المطلوب]\n```",
            color=discord.Color.from_rgb(47, 49, 54)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        channel = interaction.channel
        user = interaction.user

        def check(message):
            return message.author.id == ADAMC_BOT_ID and str(MY_USER_ID) in message.content and ("transferred" in message.content or "💰" in message.content)

        try:
            msg = await bot.wait_for('message', timeout=300.0, check=check)
            import re
            numbers = re.findall(r'\*\*(\d+)\*\*', msg.content)
            if not numbers:
                numbers = re.findall(r'\d+', msg.content)
            
            transferred_amount = int(numbers[0]) if numbers else price_per_coin
            coins_to_add = max(1, transferred_amount // price_per_coin)

            update_user_coins(user.id, coins_to_add)
            new_balance = get_user_coins(user.id)

            success_embed = discord.Embed(
                title="✅ | تمت عملية الشحن بنجاح",
                description=f"تمت إضافة **{coins_to_add} عملة** إلى رصيدك.\n💰 **رصيدك الحالي:** `{new_balance} عملة`",
                color=discord.Color.green()
            )
            await channel.send(embed=success_embed)
            await send_log_webhook("عملية شحن ناجحة", f"👤 العضو: {user.mention}\n💎 العملات: **{coins_to_add}**", discord.Color.green())

        except asyncio.TimeoutError:
            await channel.send("⏰ انتهى وقت انتظار التحويل المالي.")

    @discord.ui.button(label="🔥 شراء يوزر فوري", style=discord.ButtonStyle.green, custom_id="buy_coin_btn", emoji="🛒")
    async def buy_coin_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        balance = get_user_coins(user.id)
        cost = 3  

        if balance < cost:
            await interaction.response.send_message(embed=discord.Embed(title="❌ | رصيد غير كافٍ", description=f"رصيدك الحالي هو **{balance} عملة**.", color=discord.Color.red()), ephemeral=True)
            return

        account_item = get_and_remove_stock()
        if not account_item:
            await interaction.response.send_message(embed=discord.Embed(title="📦 | الستوك فارغ", description="مخزون اليوزرات فارغ حالياً.", color=discord.Color.orange()), ephemeral=True)
            return

        update_user_coins(user.id, -cost)
        add_history(user.id, account_item)

        try:
            await user.send(f"🎉 **مبروك يا زعيم! اليوزر الخاص بك:** `{account_item}`")
            dm_text = "✅ تم إرسال اليوزر إلى رسائلك الخاصة."
        except discord.Forbidden:
            dm_text = f"⚠️ تعذر إرسال رسالة خاصة، ها هو يوزرك:\n`{account_item}`"

        await interaction.response.send_message(embed=discord.Embed(title="🛒 | تم الشراء بنجاح", description=dm_text, color=discord.Color.gold()), ephemeral=True)
        await send_log_webhook("عملية شراء", f"👤 العضو: {user.mention}\n📦 اليوزر: `{account_item}`", discord.Color.gold())

@bot.tree.command(name="help", description="عرض لوحة المساعدة")
@bot.command(name="help", description="عرض لوحة المساعدة")
async def help_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    embed = discord.Embed(title="🌟 | لوحة المساعدة - Rayo Store", description="اختر التصنيف من القائمة أدناه:", color=discord.Color.gold())
    view = HelpView()
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="ticket", description="فتح تذكرة الشراء")
@bot.command(name="ticket", description="فتح تذكرة الشراء")
async def ticket(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    guild = ctx_or_interaction.guild
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    category = discord.utils.get(guild.categories, name="التذاكر")
    if not category:
        category = await guild.create_category("التذاكر")

    ticket_channel = await guild.create_text_channel(f"store-{user.name}", category=category, overwrites=overwrites)
    
    balance = get_user_coins(user.id)
    embed = discord.Embed(title="🌟 | متجر يوزرات ديسكورد الرسمي", description=f"مرحباً بك {user.mention}!\n💰 **رصيدك:** `{balance} عملة`", color=discord.Color.gold())
    
    await ticket_channel.send(embed=embed, view=StoreView())
    
    reply_embed = discord.Embed(title="✅ تم فتح التذكرة", description=f"توجه إلى قناتك: {ticket_channel.mention}", color=discord.Color.green())
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=reply_embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=reply_embed)

@bot.tree.command(name="wallet", description="استعراض رصيدك")
@bot.command(name="wallet", description="استعراض رصيدك")
async def wallet_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    balance = get_user_coins(user.id)
    embed = discord.Embed(title="💰 | المحفظة", description=f"رصيدك الحالي: **{balance} عملة**", color=discord.Color.blurple())
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="stock", description="عرض حالة الستوك")
@bot.command(name="stock", description="عرض حالة الستوك")
async def stock_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    total = count_stock()
    embed = discord.Embed(title="📦 | الستوك", description=f"المتوفر حالياً: **{total}** يوزر.", color=discord.Color.blurple())
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="addstock", description="إضافة يوزر للستوك")
@app_commands.describe(username="اليوزر المراد إضافته")
@bot.command(name="addstock", description="إضافة يوزر للستوك")
async def addstock_cmd(ctx_or_interaction, username: str = None):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    if user.id != MY_USER_ID:
        msg = "❌ للإدارة فقط!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return
        
    if not username:
        msg = "❌ اكتب اليوزر (مثال: `+addstock rayo`)"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    add_to_stock(username)
    total = count_stock()
    msg = f"➕ تمت إضافة اليوزر `{username}` بنجاح. الإجمالي: **{total}**"
    if is_slash:
        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
    else:
        await ctx_or_interaction.send(msg)

keep_alive()
TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not set.")
