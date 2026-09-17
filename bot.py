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

# 1. إعداد سيرفر Flask للبقاء شاعلاً 24/7 على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. إعدادات الصلاحيات والبوت مع البريڤكس (+)
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

# إزالة أمر help الافتراضي لنضع أمرنا المخصص الاحترافي
bot.remove_command('help')

ADAMC_BOT_ID = 1505622388975468684
MY_USER_ID = 1350403970132213812

WALLET_FILE = "wallet.json"
HISTORY_FILE = "history.json"
REFERRAL_FILE = "referrals.json"
DAILY_FILE = "daily.json"

LOGS_WEBHOOK_URL = "PUT_YOUR_DISCORD_WEBHOOK_URL_HERE"

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

# --- دوال إدارة الملفات ---

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

# --- دوال نظام الإحالة (Referral) ---

def get_user_referrer(user_id):
    refs = load_json(REFERRAL_FILE)
    return refs.get(str(user_id))

def set_user_referrer(user_id, referrer_id):
    refs = load_json(REFERRAL_FILE)
    uid = str(user_id)
    if uid not in refs:
        refs[uid] = str(referrer_id)
        save_json(REFERRAL_FILE, refs)
        return True
    return False

# --- دوال الستوك ---

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

def is_rare_username(username):
    clean_name = username.strip().replace("@", "")
    return len(clean_name) <= 4

# ==================== نظام السنايبر والفحص الأوتوماتيكي ====================

SNIPER_ACTIVE = False

async def check_discord_username(username, user_token=None):
    headers = {"Content-Type": "application/json"}
    if user_token:
        headers["Authorization"] = user_token
    payload = {"username": username}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("https://discord.com/api/v9/users/@me/pomelo-attempt", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("taken", True) == False
                elif resp.status == 429:
                    await asyncio.sleep(5)
                    return False
        except Exception:
            pass
    return False

# ==================== قائمة المساعدة الاحترافية (Help Dropdown) ====================

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="الأوامر العامة", description="استعراض الأوامر المتاحة لكافة الأعضاء", emoji="🌐", value="public"),
            discord.SelectOption(label="أوامر الإدارة والتذاكر", description="الأوامر الخاصة بفتح التذاكر وإدارة المبيعات", emoji="🛡️", value="admin"),
            discord.SelectOption(label="أوامر صاحب البوت (الزعيم)", description="التحكم الكامل بالستوك والسنايبر وتفريغ المخزون", emoji="👑", value="owner")
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
                            "• `/daily` أو `+daily` - استلام مكافأتك اليومية المجانية (كل 24 ساعة)\n"
                            "• `/referral` أو `+referral` - تسجيل كود إحالة صديق\n"
                            "• `/box` أو `+box` - فتح صندوق الحظ العشوائي",
                color=discord.Color.blue()
            )
        elif self.values[0] == "admin":
            embed = discord.Embed(
                title="🛡️ | أوامر الإدارة والتذاكر",
                description="الأوامر المخصصة لإدارة العمليات والمخزون:\n\n"
                            "• `/addstock` أو `+addstock` - إضافة يوزر للمخزون (مع الفلتر التلقائي)\n"
                            "• `/stock` أو `+stock` - عرض عدد اليوزرات الجاهزة للبيع\n"
                            "• `/clearstock` أو `+clearstock` - مسح وتفريغ الستوك",
                color=discord.Color.orange()
            )
        elif self.values[0] == "owner":
            embed = discord.Embed(
                title="👑 | أوامر صاحب البوت (الزعيم ريانو)",
                description="أوامر التحكم السيادية الخاصة بك وحدك:\n\n"
                            "• `/start-sniper` أو `+start-sniper` - تشغيل الفاحص والسنايبر الآلي\n"
                            "• `/stop-sniper` أو `+stop-sniper` - إيقاف عمل السنايبر في الخلفية",
                color=discord.Color.gold()
            )
        
        embed.set_footer(text="Rayo Store Elite System • استخدم الـ Prefix (+) أو Slash Commands (/)")
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

# ==================== الأزرار والتفاعل الفخم ====================

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
                        f"```text\n#credit <@{MY_USER_ID}> [المبلغ المطلوب]\n```\n"
                        f"⏳ **ملاحظة إدارية:** الكردت بيتوفر بعد رجعة بروبوت، وأرسل التحويل هنا ليتم الشحن فوراً!",
            color=discord.Color.from_rgb(47, 49, 54)
        )
        embed.set_footer(text="أرسل وصل أو رسالة التحويل في هذه التذكرة للرصد الفوري")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        channel = interaction.channel
        user = interaction.user

        def check(message):
            is_correct_bot = message.author.id == ADAMC_BOT_ID
            contains_my_id = str(MY_USER_ID) in message.content
            has_transfer_keyword = "transferred" in message.content or "💰" in message.content
            return message.channel == channel and is_correct_bot and contains_my_id and has_transfer_keyword

        try:
            msg = await bot.wait_for('message', timeout=300.0, check=check)
            content = msg.content
            import re
            numbers = re.findall(r'\*\*(\d+)\*\*', content)
            if not numbers:
                numbers = re.findall(r'\d+', content)
            
            transferred_amount = int(numbers[0]) if numbers else price_per_coin
            coins_to_add = transferred_amount // price_per_coin
            
            if coins_to_add < 1:
                coins_to_add = 1

            update_user_coins(user.id, coins_to_add)
            new_balance = get_user_coins(user.id)

            referrer_id = get_user_referrer(user.id)
            if referrer_id:
                ref_bonus = max(1, coins_to_add // 5)
                update_user_coins(int(referrer_id), ref_bonus)
                try:
                    ref_user = await bot.fetch_user(int(referrer_id))
                    await ref_user.send(f"🎁 لقد حصلت على **{ref_bonus} عملة** عمولة إحالة لأن الصديق الذي دعوته قام بشحن رصيده!")
                except Exception:
                    pass

            success_embed = discord.Embed(
                title="✅ | تمت عملية الشحن بنجاح",
                description=f"تم رصد تحويلك المالي وإضافة **{coins_to_add} عملة** إلى رصيدك.\n💰 **رصيدك الحالي:** `{new_balance} عملة`",
                color=discord.Color.green()
            )
            await channel.send(embed=success_embed)
            await send_log_webhook("عملية شحن ناجحة", f"👤 العضو: {user.mention} (`{user.id}`)\n💎 العملات المضافة: **{coins_to_add}**\n💰 الرصيد الجديد: **{new_balance}**", discord.Color.green())

        except asyncio.TimeoutError:
            await channel.send("⏰ انتهى وقت انتظار التحويل المالي للشحن التلقائي.")

    @discord.ui.button(label="🔥 شراء يوزر فوري", style=discord.ButtonStyle.green, custom_id="buy_coin_btn", emoji="🛒")
    async def buy_coin_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        balance = get_user_coins(user.id)
        cost = 3  

        if balance < cost:
            fail_embed = discord.Embed(
                title="❌ | رصيد غير كافٍ",
                description=f"عذراً، رصيدك الحالي هو **{balance} عملة** فقط.\nتحتاج إلى **{cost} عملات** لاقتناء يوزر من المتجر.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=fail_embed, ephemeral=True)
            return

        account_item = get_and_remove_stock()
        if not account_item:
            empty_embed = discord.Embed(
                title="📦 | الستوك فارغ",
                description="عذراً، مخزون اليوزرات فارغ حالياً. ترقب الإضافات القادمة قريباً!",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=empty_embed, ephemeral=True)
            return

        update_user_coins(user.id, -cost)
        add_history(user.id, account_item)

        try:
            await user.send(f"🎉 **مبروك يا زعيم! لقد استبدلت عملاتك بنجاح:**\n اليوزر الخاص بك: `{account_item}`")
            dm_text = "✅ تم إرسال معلومات اليوزر إلى رسائلك الخاصة (DM) بسرية تامة."
        except discord.Forbidden:
            dm_text = f"⚠️ تعذر إرسال رسالة خاصة، ها هو يوزرك هنا:\n`{account_item}`"

        success_buy = discord.Embed(
            title="🛒 | تم الشراء بنجاح",
            description=f"{dm_text}\n🔒 تم خصم **{cost} عملات** من محفظتك.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=success_buy, ephemeral=True)
        await send_log_webhook("عملية شراء يوزر", f"👤 العضو: {user.mention} (`{user.id}`)\n📦 اليوزر: `{account_item}`\n💸 التكلفة: **{cost} عملات**", discord.Color.gold())

# ==================== الأوامر (تخدم بالـ Slash وبـ Prefix + معاً) ====================

@bot.tree.command(name="help", description="عرض لوحة المساعدة وقائمة الأوامر الاحترافية")
@bot.command(name="help", description="عرض لوحة المساعدة وقائمة الأوامر الاحترافية")
async def help_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    embed = discord.Embed(
        title="🌟 | لوحة المساعدة والتحكم - Rayo Store",
        description=f"مرحباً بك يا {user.mention} في نظام المتجر الاحترافي.\n\n"
                    f"استخدم قائمة الاختيار أدناه لتصنيف الأوامر التي تريد استعراضها:",
        color=discord.Color.from_rgb(255, 215, 0)
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="اختر التصنيف من القائمة أدناه • البوت يعمل بنظام البريڤكس (+) والـ Slash (/)")
    
    view = HelpView()
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed, view=view)

@bot.tree.command(name="ticket", description="فتح تذكرة الشراء والتعامل بعملات المتجر الرسمية")
@bot.command(name="ticket", description="فتح تذكرة الشراء والتعامل بعملات المتجر الرسمية")
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
    embed = discord.Embed(
        title="🌟 | متجر يوزرات ديسكورد الرسمي",
        description=f"مرحباً بك في تذكرتك الخاصة {user.mention}!\n\n"
                    f"💰 **رصيدك الحالي:** `{balance} عملة متجر`\n\n"
                    f"استخدم الأزرار أدناه للتحكم الكامل (شحن أوتوماتيكي أو شراء فوري):",
        color=discord.Color.from_rgb(255, 215, 0)
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="نظام المتجر الآمن • خدمة مميزة 24/7")
    
    await ticket_channel.send(embed=embed, view=StoreView())
    
    reply_embed = discord.Embed(title="✅ تم فتح التذكرة بنجاح", description=f"توجه إلى قناتك الخاصة هنا: {ticket_channel.mention}", color=discord.Color.green())
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=reply_embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=reply_embed)
    await send_log_webhook("فتح تذكرة جديدة", f"👤 العضو: {user.mention}\n📌 القناة: {ticket_channel.mention}", discord.Color.blurple())

@bot.tree.command(name="wallet", description="استعراض رصيدك الحالي من عملات المتجر الفاخرة")
@bot.command(name="wallet", description="استعراض رصيدك الحالي من عملات المتجر الفاخرة")
async def wallet_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    balance = get_user_coins(user.id)
    
    embed = discord.Embed(
        title="💰 | المحفظة الرقمية",
        description=f"رصيدك المتوفر حالياً هو: **{balance} عملة متجر**",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="history", description="عرض سجل آخر يوزرات قمت باكتسابها واشترائها")
@bot.command(name="history", description="عرض سجل آخر يوزرات قمت باكتسابها واشترائها")
async def history_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    history = load_json(HISTORY_FILE)
    user_items = history.get(str(user.id), [])
    
    if not user_items:
        embed = discord.Embed(title="📜 | سجل المشتريات", description="سجلك نظيف، ليس لديك أي عمليات شراء سابقة حتى الآن.", color=discord.Color.red())
    else:
        items_str = "\n".join([f"• `{item}`" for item in user_items[-10:]])
        embed = discord.Embed(title="📜 | سجل مشترياتك السابقة", description=items_str, color=discord.Color.green())
    
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="store-info", description="عرض إحصائيات المتجر الشاملة وحالة المخزون")
@bot.command(name="store-info", description="عرض إحصائيات المتجر الشاملة وحالة المخزون")
async def store_info_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    total_stock = count_stock()
    total_sales = get_total_sales_count()
    
    embed = discord.Embed(
        title="📊 | لوحة إحصائيات المتجر الملكي",
        description="معلومات دقيقة حول أداء وحجم متجر اليوزرات:",
        color=discord.Color.from_rgb(0, 150, 255)
    )
    embed.add_field(name="📦 اليوزرات المتاحة حالياً", value=f"`{total_stock}` يوزر", inline=True)
    embed.add_field(name="🛒 إجمالي المبيعات", value=f"`{total_sales}` عملية ناجحة", inline=True)
    embed.add_field(name="💎 سعر العملة الواحدة", value="`800k` كريديت", inline=False)
    embed.set_footer(text="متجر موثوق وآمن للجميع")
    
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="daily", description="الحصول على مكافأتك اليومية المجانية من عملات المتجر")
@bot.command(name="daily", description="الحصول على مكافأتك اليومية المجانية من عملات المتجر")
async def daily_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    user_id_str = str(user.id)
    daily_data = load_json(DAILY_FILE)
    
    now = datetime.utcnow()
    if user_id_str in daily_data:
        last_claim = datetime.fromisoformat(daily_data[user_id_str])
        next_claim_time = last_claim + timedelta(hours=24)
        if now < next_claim_time:
            remaining = next_claim_time - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            
            embed_err = discord.Embed(
                title="⏳ | المكافأة اليومية مستحقة لاحقاً",
                description=f"لقد استلمت مكافأتك اليومية مسبقاً!\nيرجى الانتظار **{hours} ساعة** و **{minutes} دقيقة** لاستلام المكافأة القادمة.",
                color=discord.Color.orange()
            )
            if is_slash:
                await ctx_or_interaction.response.send_message(embed=embed_err, ephemeral=True)
            else:
                await ctx_or_interaction.send(embed=embed_err)
            return

    daily_data[user_id_str] = now.isoformat()
    save_json(DAILY_FILE, daily_data)
    
    update_user_coins(user.id, 1)
    new_bal = get_user_coins(user.id)
    
    embed_ok = discord.Embed(
        title="🎉 | تم استلام المكافأة اليومية بنجاح",
        description=f"مبروك! حصلت على **1 عملة متجر مجانية**.\n💰 رصيدك الحالي: `{new_bal} عملة`",
        color=discord.Color.green()
    )
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed_ok, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed_ok)
    await send_log_webhook("مكافأة يومية", f"👤 العضو: {user.mention} استلم مكافئته اليومية.", discord.Color.green())

@bot.tree.command(name="start-sniper", description="تشغيل السنايبر والفاحص الآلي لبيانات وتوكن الحساب")
@app_commands.describe(user_token="ضع توكن الحساب القديم الخاص بك هنا للفحص الآمن")
@bot.command(name="start-sniper", description="تشغيل السنايبر والفاحص الآلي")
async def start_sniper_cmd(ctx_or_interaction, user_token: str = None):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    if user.id != MY_USER_ID:
        msg = "❌ للإدارة العليا فقط!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return
    
    if not user_token:
        msg = "❌ يرجى إدخال التوكن مع الأمر (مثال بالبريڤكس: `+start-sniper YOUR_TOKEN`)"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return
    
    global SNIPER_ACTIVE
    SNIPER_ACTIVE = True
    
    success_msg = "🚀 **تم تشغيل السنايبر والفاحص الآلي بنجاح!**\nالبوت بدأ يفحص اليوزرات في الخلفية ويتأكد من إتاحتها قبل فرزها للستوك أو لخاصك."
    if is_slash:
        await ctx_or_interaction.response.send_message(success_msg, ephemeral=True)
    else:
        await ctx_or_interaction.send(success_msg)
    
    async def run_sniper_background():
        global SNIPER_ACTIVE
        sample_bases = ["rayo", "apex", "king", "god", "x9", "z_1", "vibe", "core", "neon", "cyber"]
        while SNIPER_ACTIVE:
            try:
                rand_num = random.randint(10, 999)
                base = random.choice(sample_bases)
                test_username = f"{base}{rand_num}"
                
                is_available = await check_discord_username(test_username, user_token)
                
                if is_available:
                    if is_rare_username(test_username):
                        try:
                            owner = await bot.fetch_user(MY_USER_ID)
                            await owner.send(f"⭐ **[سنايبر] يوزر فخم ومتاح شغال!**\nاليوزر: `{test_username}`\nتم إرساله إليك حصرياً.")
                        except Exception:
                            pass
                    else:
                        add_to_stock(test_username)
                        await send_log_webhook("سنايبر يوزر جديد", f"تم العثور على يوزر متاح وإضافته للستوك: `{test_username}`", discord.Color.green())
                
                await asyncio.sleep(15)
            except Exception:
                await asyncio.sleep(10)

    bot.loop.create_task(run_sniper_background())

@bot.tree.command(name="stop-sniper", description="إيقاف عمل السنايبر والفاحص الآلي")
@bot.command(name="stop-sniper", description="إيقاف عمل السنايبر والفاحص الآلي")
async def stop_sniper_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    if user.id != MY_USER_ID:
        msg = "❌ للإدارة فقط!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return
    
    global SNIPER_ACTIVE
    SNIPER_ACTIVE = False
    msg = "🛑 **تم إيقاف السنايبر والفاحص الآلي بنجاح.**"
    if is_slash:
        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
    else:
        await ctx_or_interaction.send(msg)

@bot.tree.command(name="addstock", description="إضافة يوزر للمخزون مع فلتر أوتوماتيكي لليوزرات المميزة")
@app_commands.describe(username="اكتب اليوزر المراد إضافته")
@bot.command(name="addstock", description="إضافة يوزر للمخزون")
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
        msg = "❌ يرجى كتابة اليوزر مع الأمر (مثال: `+addstock rayo`)"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return

    if is_rare_username(username):
        try:
            owner = await bot.fetch_user(MY_USER_ID)
            await owner.send(f"⭐ **يوزر مميز / شبه ثلاثي جديد!**\nاليوزر: `{username}`\nتم عزله عن الستوك العام وإرساله إليك حصرياً.")
        except Exception:
            pass
        msg = f"⭐ اليوزر `{username}` يعتبر مميزاً، وتم إرساله لخاصك السري ولم يُضاف للعام!"
    else:
        add_to_stock(username)
        total = count_stock()
        msg = f"➕ تمت إضافة اليوزر `{username}` بنجاح للستوك العام. الإجمالي الحالي: **{total}**"
        
    if is_slash:
        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
    else:
        await ctx_or_interaction.send(msg)

@bot.tree.command(name="stock", description="استعراض حالة الستوك وعدد اليوزرات الجاهزة للبيع")
@bot.command(name="stock", description="استعراض حالة الستوك")
async def stock_cmd(ctx_or_interaction):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    total = count_stock()
    embed = discord.Embed(
        title="📦 | حالة مخزون الستوك",
        description=f"إجمالي اليوزرات المتوفرة حالياً في الشيكورة: **{total}** يوزر جاهز للبيع الفوري.",
        color=discord.Color.blurple()
    )
    if is_slash:
        await ctx_or_interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await ctx_or_interaction.send(embed=embed)

@bot.tree.command(name="clearstock", description="تفريغ الستوك بالكامل للإدارة")
@app_commands.describe(tier="حدد نوع الستوك المراد مسحه")
@app_commands.choices(tier=[
    app_commands.Choice(name="عام (Public)", value="public"),
    app_commands.Choice(name="مميز (Rare)", value="rare"),
    app_commands.Choice(name="الكل (All)", value="all")
])
@bot.command(name="clearstock", description="تفريغ الستوك بالكامل")
async def clearstock_cmd(ctx_or_interaction, tier: str = "all"):
    is_slash = isinstance(ctx_or_interaction, discord.Interaction)
    user = ctx_or_interaction.user if is_slash else ctx_or_interaction.author
    
    if user.id != MY_USER_ID:
        msg = "❌ لأصحاب المتجر فقط!"
        if is_slash:
            await ctx_or_interaction.response.send_message(msg, ephemeral=True)
        else:
            await ctx_or_interaction.send(msg)
        return
    
    if tier in ["public", "all"]:
        clear_stock_file()
        
    msg = f"🧹 تم تفريغ الستوك ({tier}) بنجاح تام."
    if is_slash:
        await ctx_or_interaction.response.send_message(msg, ephemeral=True)
    else:
        await ctx_or_interaction.send(msg)

keep_alive()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable not set.")
