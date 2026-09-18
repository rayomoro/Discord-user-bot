import os
import json
import asyncio
import random
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import aiohttp
from datetime import datetime

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
                            "• `/ticket` - فتح تذكرة شراء جديدة\n"
                            "• `/wallet` - فحص رصيدك من عملات Rex Coin\n"
                            "• `/stock` - عرض الستوك المتوفر\n"
                            "• `/pay` - تحويل عملات لعضو آخر\n"
                            "• `/history` - عرض سجل مشترياتك السابقة\n"
                            "• `/vouch` - تقييم المتجر",
                color=discord.Color.blue()
            )
        elif self.values[0] == "admin":
            embed = discord.Embed(
                title="🛡️ | أوامر الإدارة والتذاكر",
                description="الأوامر المخصصة للإدارة:\n\n"
                            "• `/ticket-panel` - إرسال بنل التذاكر في القناة\n"
                            "• `/autorefresh` - إرسال الستوك للخاص للتحقق\n"
                            "• `/autostock` - توليد يوزرات أوتوماتيكياً\n"
                            "• `/addrex` - إضافة عملات لعضو\n"
                            "• `/addstock` - إضافة يوزر للمخزون",
                color=discord.Color.orange()
            )
        embed.set_footer(text="Rayo Store Elite System • نظام متكامل")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

class MainTicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 فتح تذكرة شراء", style=discord.ButtonStyle.green, custom_id="create_ticket_main_btn", emoji="🛒")
    async def create_ticket_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket_process(interaction)

class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💳 شحن Rex Coin أوتوماتيكياً", style=discord.ButtonStyle.blurple, custom_id="deposit_btn", emoji="💎")
    async def deposit_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        price_per_coin = 800000
        embed = discord.Embed(
            title="💎 | نظام الشحن التلقائي الفخم",
            description=f"مرحباً بك في بوابة الشحن الرسمية للمتجر.\n\n"
                        f"📌 **التسعيرة:** كل **1 Rex Coin** بـ **800k** كريديت.\n"
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
                description=f"تمت إضافة **{coins_to_add} Rex Coin** إلى رصيدك.\n💰 **رصيدك الحالي:** `{new_balance} Rex Coin`",
                color=discord.Color.green()
            )
            await channel.send(embed=success_embed)
            await send_log_webhook("عملية شحن ناجحة", f"👤 العضو: {user.mention}\n💎 العملات: **{coins_to_add} Rex Coin**", discord.Color.green())

        except asyncio.TimeoutError:
            await channel.send("⏰ انتهى وقت انتظار التحويل المالي.")

    @discord.ui.button(label="🔥 شراء يوزر فوري", style=discord.ButtonStyle.green, custom_id="buy_coin_btn", emoji="🛒")
    async def buy_coin_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        balance = get_user_coins(user.id)
        cost = 3  

        if balance < cost:
            await interaction.response.send_message(embed=discord.Embed(title="❌ | رصيد غير كافٍ", description=f"رصيدك الحالي هو **{balance} Rex Coin**.", color=discord.Color.red()), ephemeral=True)
            return

        account_item = get_and_remove_stock()
        if not account_item:
            await interaction.response.send_message(embed=discord.Embed(title="📦 | الستوك فارغ", description="مخزون اليوزرات فارغ حالياً.", color=discord.Color.orange()), ephemeral=True)
            return

        update_user_coins(user.id, -cost)
        add_history(user.id, account_item)

        # نظام تنبيه انتهاء الستوك أوتوماتيكياً عبر الـ Webhook
        remaining_stock = count_stock()
        if remaining_stock <= 2:
            await send_log_webhook("⚠️ تنبيه: الستوك يوشك على النفاد!", f"📦 المتبقي حالياً في الستوك: **{remaining_stock} يوزر فقط!**\nيرجى تجديده بسرعة عبر أمر `/autostock`.", discord.Color.orange())

        try:
            await user.send(f"🎉 **مبروك يا زعيم! اليوزر الخاص بك:** `{account_item}`")
            dm_text = "✅ تم إرسال اليوزر إلى رسائلك الخاصة."
        except discord.Forbidden:
            dm_text = f"⚠️ تعذر إرسال رسالة خاصة، ها هو يوزرك:\n`{account_item}`"

        await interaction.response.send_message(embed=discord.Embed(title="🛒 | تم الشراء بنجاح", description=dm_text, color=discord.Color.gold()), ephemeral=True)
        await send_log_webhook("عملية شراء", f"👤 العضو: {user.mention}\n📦 اليوزر: `{account_item}`\n📉 المتبقي بالستوك: `{remaining_stock}`", discord.Color.gold())

async def open_ticket_process(interaction_or_ctx):
    is_slash = isinstance(interaction_or_ctx, discord.Interaction)
    guild = interaction_or_ctx.guild
    user = interaction_or_ctx.user if is_slash else interaction_or_ctx.author
    
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
    embed = discord.Embed(title="🌟 | متجر يوزرات ديسكورد الرسمي", description=f"مرحباً بك {user.mention}!\n💰 **رصيدك:** `{balance} Rex Coin`", color=discord.Color.gold())
    
    await ticket_channel.send(embed=embed, view=StoreView())
    
    reply_embed = discord.Embed(title="✅ تم فتح التذكرة", description=f"توجه إلى قناتك: {ticket_channel.mention}", color=discord.Color.green())
    if is_slash:
        await interaction_or_ctx.response.send_message(embed=reply_embed, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=reply_embed)

@bot.tree.command(name="help", description="عرض لوحة المساعدة")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🌟 | لوحة المساعدة - Rayo Store", description="اختر التصنيف من القائمة أدناه:", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

@bot.tree.command(name="ticket", description="فتح تذكرة الشراء")
async def ticket_cmd(interaction: discord.Interaction):
    await open_ticket_process(interaction)

@bot.tree.command(name="ticket-panel", description="إرسال رسالة نظام التذاكر في القناة")
async def ticket_panel_cmd(interaction: discord.Interaction):
    if interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ للإدارة فقط!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎫 | نظام تذاكر متجر Rayo Store",
        description="اضغط على الزر أدناه لفتح تذكرة شراء جديدة واستكشاف الستوك والأسعار بكل راحتك!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Rayo Store Elite System • 2026")
    
    await interaction.response.send_message("✅ تم إرسال بنل التذاكر بنجاح.", ephemeral=True)
    await interaction.channel.send(embed=embed, view=MainTicketPanelView())

@bot.tree.command(name="autorefresh", description="إرسال كافة يوزرات الستوك للخاص للتحقق اليدوي منها")
async def autorefresh_cmd(interaction: discord.Interaction):
    if interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب البوت فقط!", ephemeral=True)
        return

    await interaction.response.send_message("📤 جاري إرسال قائمة الستوك كاملة إلى رسائلك الخاصة للتحقق اليدوي...", ephemeral=True)
    lines = load_stock_lines()
    if not lines:
        try:
            owner_user = await bot.fetch_user(MY_USER_ID)
            await owner_user.send("📦 الستوك فارغ تماماً حالياً!")
        except Exception:
            pass
        return

    try:
        owner_user = await bot.fetch_user(MY_USER_ID)
        chunk = "📋 **قائمة يوزرات الستوك الحالية للتحقق اليدوي:**\n"
        for idx, item in enumerate(lines, 1):
            line_str = f"{idx}. `{item}`\n"
            if len(chunk) + len(line_str) > 1900:
                await owner_user.send(chunk)
                chunk = ""
            chunk += line_str
        if chunk:
            await owner_user.send(chunk)
        await owner_user.send(f"✅ **تم إرسال إجمالي {len(lines)} يوزر بنجاح. راجعهم وقم بحذف التالف يدويًا.**")
    except Exception as e:
        print(f"Error sending stock to DM: {e}")

@bot.tree.command(name="autostock", description="تجديد الستوك أوتوماتيكياً بدون سنايب")
@app_commands.describe(count="عدد اليوزرات المراد توليدها أوتوماتيكياً")
async def autostock_cmd(interaction: discord.Interaction, count: int = 5):
    if interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب البوت فقط!", ephemeral=True)
        return

    letters = "abcdefghijklmnopqrstuvwxyz0123456789_"
    for _ in range(count):
        uname = "".join(random.choices(letters, k=4)) + "_" + "".join(random.choices(letters, k=2))
        add_to_stock(uname)

    total = count_stock()
    await interaction.response.send_message(f"✨ تمت إضافة **{count} يوزر** أوتوماتيكياً للستوك بنجاح!\n📦 الإجمالي الحالي: **{total}** يوزر.", ephemeral=True)

@bot.tree.command(name="addrex", description="إضافة عملات Rex Coin لشخص معين")
@app_commands.describe(member="العضو المراد إضافة العملات له", amount="عدد عملات Rex Coin المراد إضافتها")
async def addrex_cmd(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب البوت فقط!", ephemeral=True)
        return

    update_user_coins(member.id, amount)
    new_balance = get_user_coins(member.id)
    await interaction.response.send_message(f"✅ تمت إضافة **{amount} Rex Coin** بنجاح إلى العضو {member.mention}.\n💰 رصيده الجديد: `{new_balance} Rex Coin`", ephemeral=True)

@bot.tree.command(name="wallet", description="استعراض رصيدك من Rex Coin")
async def wallet_cmd(interaction: discord.Interaction):
    balance = get_user_coins(interaction.user.id)
    embed = discord.Embed(title="💰 | المحفظة", description=f"رصيدك الحالي: **{balance} Rex Coin**", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stock", description="عرض حالة الستوك")
async def stock_cmd(interaction: discord.Interaction):
    total = count_stock()
    embed = discord.Embed(title="📦 | الستوك", description=f"المتوفر حالياً: **{total}** يوزر.", color=discord.Color.blurple())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="addstock", description="إضافة يوزر للستوك")
@app_commands.describe(username="اليوزر المراد إضافته")
async def addstock_cmd(interaction: discord.Interaction, username: str):
    if interaction.user.id != MY_USER_ID:
        await interaction.response.send_message("❌ للإدارة فقط!", ephemeral=True)
        return

    add_to_stock(username)
    total = count_stock()
    await interaction.response.send_message(f"➕ تمت إضافة اليوزر `{username}` بنجاح. الإجمالي: **{total}**", ephemeral=True)

@bot.tree.command(name="pay", description="تحويل عملات Rex Coin لعضو آخر")
@app_commands.describe(member="العضو المراد التحويل له", amount="عدد العملات")
async def pay_cmd(interaction: discord.Interaction, member: discord.Member, amount: int):
    user = interaction.user
    if amount <= 0:
        await interaction.response.send_message("❌ لا يمكنك تحويل قيمة سالبة أو صفر!", ephemeral=True)
        return
    if member.id == user.id:
        await interaction.response.send_message("❌ لا يمكنك التحويل لنفسك!", ephemeral=True)
        return

    sender_balance = get_user_coins(user.id)
    if sender_balance < amount:
        await interaction.response.send_message(f"❌ رصيدك غير كافٍ! رصيدك الحالي: `{sender_balance} Rex Coin`", ephemeral=True)
        return

    update_user_coins(user.id, -amount)
    update_user_coins(member.id, amount)

    await interaction.response.send_message(f"✅ تم تحويل **{amount} Rex Coin** بنجاح إلى العضو {member.mention}!", ephemeral=True)
    await send_log_webhook("تحويل مالي بين الأعضاء", f"👤 من: {user.mention}\n👤 إلى: {member.mention}\n💎 الكمية: **{amount} Rex Coin**", discord.Color.blue())

@bot.tree.command(name="history", description="عرض سجل يوزراتك المشراة سابقاً")
async def history_cmd(interaction: discord.Interaction):
    history_data = load_json(HISTORY_FILE)
    user_history = history_data.get(str(interaction.user.id), [])

    if not user_history:
        embed = discord.Embed(title="📜 | سجل المشتريات", description="ليس لديك أي مشتريات سابقة في سجلك.", color=discord.Color.orange())
    else:
        items_str = "\n".join([f"• `{item}`" for item in user_history[-15:]])
        embed = discord.Embed(title="📜 | سجل مشترياتك الأخيرة", description=items_str, color=discord.Color.gold())

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="vouch", description="تقييم متجر Rayo Store وثقة التعامل")
@app_commands.describe(rating="التقييم من 1 إلى 5", comment="رأيك في المتجر والخدمة")
async def vouch_cmd(interaction: discord.Interaction, rating: int, comment: str):
    if rating < 1 or rating > 5:
        await interaction.response.send_message("❌ التقييم يجب أن يكون بين 1 و 5 نجوم!", ephemeral=True)
        return

    stars = "⭐" * rating
    await interaction.response.send_message("✅ شكراً لك! تم إرسال تقييمك بنجاح.", ephemeral=True)
    await send_log_webhook("تقييم جديد (Vouch)", f"👤 العضو: {interaction.user.mention}\n⭐ التقييم: {rating}/5 ({stars})\n💬 التعليق: {comment}", discord.Color.gold())

keep_alive()
TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not set.")
