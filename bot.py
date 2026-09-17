import os
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread

# 1. إعداد سيرفر Flask للحفاظ على البوت شاعلاً 24/7 على Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. إعدادات البوت والصلاحيات
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # مزامنة الأوامر التفاعلية (Slash Commands) مع ديسكورد
        await self.tree.sync()
        print("Slash commands synced successfully.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('Bot is online and ready!')

# ==================== الأوامر التفاعلية (Slash Commands) ====================

# أمر عرض الستوك والمنتجات
@bot.tree.command(name="stock", description="عرض المنتجات المتوفرة في المتجر حالياً")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📦 متجر السلع والخدمات",
        description="المنتجات المتوفرة حالياً:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🔹 حسابات نتفليكس", value="السعر: متوفر - اضغط فتح تذكرة للشراء", inline=False)
    embed.add_field(name="🔹 رتب ديسكورد Nitro", value="السعر: متوفر - تواصل مع الإدارة", inline=False)
    embed.set_footer(text="لشراء أي منتج، افتح تذكرة جديدة أدناه.")
    await interaction.response.send_message(embed=embed, ephemeral=False)

# نظام فتح التذاكر (Ticket System)
@bot.tree.command(name="ticket", description="فتح تذكرة جديدة للتواصل مع الإدارة أو الشراء")
async def ticket(interaction: discord.Interaction):
    guild = interaction.guild
    # البحث عن رتبة المشرفين أو الصلاحيات (يمكن تعديل الفئة لاحقاً)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    # إنشاء قناة جديدة خاصة بالتذكرة
    category = discord.utils.get(guild.categories, name="التذاكر")
    if not category:
        category = await guild.create_category("التذاكر")

    channel_name = f"ticket-{interaction.user.name}"
    ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
    
    embed = discord.Embed(
        title="🎫 تذكرة جديدة",
        description=f"مرحباً بك {interaction.user.mention}! تم فتح التذكرة بنجاح. اكتب طلبك هنا وسيرد عليك الإداريون في أقرب وقت.",
        color=discord.Color.green()
    )
    await ticket_channel.send(embed=embed)
    await interaction.response.send_message(f"✅ تم فتح تذكرتك بنجاح في القناة: {ticket_channel.mention}", ephemeral=True)

# أمر المساعدة العام
@bot.tree.command(name="help", description="عرض قائمة أوامر البوت المتاحة")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛠️ قائمة أوامر المتجر",
        color=discord.Color.gold()
    )
    embed.add_field(name="/stock", value="لعرض المنتجات والأسعار المتوفرة.", inline=False)
    embed.add_field(name="/ticket", value="فتح تذكرة خاصة للشراء أو الاستفسار.", inline=False)
    embed.add_field(name="/help", value="عرض هذه القائمة.", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# تشغيل السيرفر الوهمي والبوت
keep_alive()

TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable not set.")
