import discord
from discord.ext import commands, tasks
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

MODERATOR_ROLES = ['mod', 'moderator', 'staff']  # Change these to your actual "mod" or "staff" role names (lowercase)

banned_words = []
banned_word_mute_time = 60  # Default mute time in seconds

# ========== Helper functions ===========
def has_role(user, role_names):
    return any(role.name.lower() in role_names for role in user.roles)

async def is_mod(ctx):
    return has_role(ctx.author, MODERATOR_ROLES) or ctx.author.guild_permissions.administrator

def human_count(guild):
    return sum(1 for member in guild.members if not member.bot)

# ========== Commands ==========

@bot.command()
async def serverstats(ctx):
    if not await is_mod(ctx): return
    guild = ctx.guild
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    total_channels = text_channels + voice_channels
    roles = len(guild.roles)
    emojis = len(guild.emojis)
    stickers = len(getattr(guild, 'stickers', []))
    animated_emojis = len([e for e in guild.emojis if e.animated])
    total_members = guild.member_count
    humans = human_count(guild)
    created = guild.created_at.strftime('%Y-%m-%d %H:%M:%S')
    await ctx.send(
        f"**Server Stats:**\n"
        f"Total Members: {total_members}\n"
        f"Humans: {humans}\n"
        f"Roles: {roles}\n"
        f"Emojis: {emojis}\n"
        f"Stickers: {stickers}\n"
        f"Animated Emojis: {animated_emojis}\n"
        f"Channels: {total_channels} (Text: {text_channels}, Voice: {voice_channels})\n"
        f"Server Created: {created}"
    )

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def mute(ctx, member: discord.Member, time: str):
    duration_sec = parse_time(time)
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted")
    await member.add_roles(muted_role)
    await ctx.send(f"{member.mention} muted for {time}")
    await asyncio.sleep(duration_sec)
    await member.remove_roles(muted_role)
    await ctx.send(f"{member.mention} unmuted.")

def parse_time(timestr):
    # Basic parser for "1m", "2h30m", etc
    import re
    time_units = {"s":1, "m":60, "h":3600, "d":86400, "w":604800, "mo":2628000, "y":31536000}
    total = 0
    pieces = re.findall(r'(\d+)([a-zA-Z]+)', timestr)
    for value, unit in pieces:
        unit = unit.lower()
        if unit in time_units:
            total += int(value) * time_units[unit]
        elif unit == 'mo':
            total += int(value) * time_units['mo']
    return total if total > 0 else 60  # default 60s

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def lock(ctx):
    overwrite = discord.PermissionOverwrite(send_messages=False)
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("Channel locked.")

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=None)
    await ctx.send("Channel unlocked.")

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def tempban(ctx, member: discord.Member, time: str):
    duration_sec = parse_time(time)
    await ctx.guild.ban(member)
    await ctx.send(f"{member.mention} is banned for {time}")
    await asyncio.sleep(duration_sec)
    await ctx.guild.unban(member)
    await ctx.send(f"{member.mention} is unbanned.")

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def roleall(ctx, role: discord.Role):
    for member in ctx.guild.members:
        await member.add_roles(role)
    await ctx.send(f"{role.name} given to all members.")

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def sendembed(ctx, *, message):
    embed = discord.Embed(description=message)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def bannedwords(ctx):
    await ctx.send(f"Banned words: {', '.join(banned_words)}")

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def bannedword(ctx, action, word=None):
    global banned_words
    if action == 'add' and word:
        banned_words.append(word)
        await ctx.send(f"Added {word} to banned words.")
    elif action == 'remove' and word:
        banned_words = [w for w in banned_words if w != word]
        await ctx.send(f"Removed {word} from banned words.")
    else:
        await ctx.send("Usage: !bannedword add/remove <word>")

@bot.command()
@commands.has_any_role(*MODERATOR_ROLES)
async def bannedwordmute(ctx, time: str):
    global banned_word_mute_time
    banned_word_mute_time = parse_time(time)
    await ctx.send(f"Banned word mute time set to: {time}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if not has_role(message.author, MODERATOR_ROLES):
        for word in banned_words:
            if word in message.content.lower():
                await message.delete()
                muted_role = discord.utils.get(message.guild.roles, name="Muted")
                if not muted_role:
                    muted_role = await message.guild.create_role(name="Muted")
                await message.author.add_roles(muted_role)
                await message.channel.send(f"{message.author.mention} was muted for saying a banned word!")
                await asyncio.sleep(banned_word_mute_time)
                await message.author.remove_roles(muted_role)
                return
    await bot.process_commands(message)

bot.run(os.getenv("DISCORD_TOKEN"))
