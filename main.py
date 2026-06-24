import discord
from discord.ext import commands
import sqlite3
from datetime import datetime
import os

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

db = sqlite3.connect("streaks.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS streaks (
    user_id INTEGER PRIMARY KEY,
    streak INTEGER,
    last_post TEXT,
    points INTEGER DEFAULT 0,
    text_done INTEGER DEFAULT 0,
    image_done INTEGER DEFAULT 0,
    music_done INTEGER DEFAULT 0
)
""")

db.commit()


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):

    if message.author.bot:
        return

    if message.channel.name != "päivän-kuuluminen":
        return

    user_id = message.author.id
    today = str(datetime.utcnow().date())

    cursor.execute("""
        SELECT streak, last_post, points,
               text_done, image_done, music_done
        FROM streaks
        WHERE user_id=?
    """, (user_id,))

    row = cursor.fetchone()

    has_text = len(message.content.strip()) > 0
    has_image = len(message.attachments) > 0

    music_sites = [
        "spotify.com",
        "youtube.com",
        "youtu.be",
        "soundcloud.com"
    ]

    has_music = any(
        site in message.content.lower()
        for site in music_sites
    )

    if row is None:

        points = 0

        text_done = 1 if has_text else 0
        image_done = 1 if has_image else 0
        music_done = 1 if has_music else 0

        points += text_done
        points += image_done
        points += music_done

        cursor.execute("""
            INSERT INTO streaks
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            1,
            today,
            points,
            text_done,
            image_done,
            music_done
        ))

        db.commit()

        await message.add_reaction("🔥")

    else:

        streak, last_post, points, text_done, image_done, music_done = row

        if last_post != today:

            last_date = datetime.strptime(
                last_post,
                "%Y-%m-%d"
            ).date()

            current_date = datetime.strptime(
                today,
                "%Y-%m-%d"
            ).date()

            days = (current_date - last_date).days

            if days == 1:

                streak += 1

                await message.reply(
                    f"🔥 Streak kasvoi! Nyt {streak} päivää putkeen."
                )

            else:

                streak = 1

                await message.reply(
                    "💔 Putki katkesi. Aloitit uuden streakin!"
                )

            text_done = 0
            image_done = 0
            music_done = 0

        earned = 0

        if has_text and text_done == 0:
            points += 1
            earned += 1
            text_done = 1

        if has_image and image_done == 0:
            points += 1
            earned += 1
            image_done = 1

        if has_music and music_done == 0:
            points += 1
            earned += 1
            music_done = 1

        cursor.execute("""
            UPDATE streaks
            SET streak=?,
                last_post=?,
                points=?,
                text_done=?,
                image_done=?,
                music_done=?
            WHERE user_id=?
        """, (
            streak,
            today,
            points,
            text_done,
            image_done,
            music_done,
            user_id
        ))

        db.commit()

        if earned > 0:
            await message.add_reaction("⭐")

    await bot.process_commands(message)


@bot.tree.command(
    name="streak",
    description="Näytä oma streak"
)
async def streak(interaction: discord.Interaction):

    cursor.execute(
        "SELECT streak FROM streaks WHERE user_id=?",
        (interaction.user.id,)
    )

    row = cursor.fetchone()

    if row:
        await interaction.response.send_message(
            f"🔥 Sinulla on {row[0]} päivän streak."
        )
    else:
        await interaction.response.send_message(
            "Et ole aloittanut streakia vielä."
        )


@bot.tree.command(
    name="points",
    description="Näytä pisteesi"
)
async def points(interaction: discord.Interaction):

    cursor.execute(
        "SELECT points FROM streaks WHERE user_id=?",
        (interaction.user.id,)
    )

    row = cursor.fetchone()

    if row:
        await interaction.response.send_message(
            f"⭐ Sinulla on {row[0]} pistettä."
        )
    else:
        await interaction.response.send_message(
            "Ei pisteitä vielä."
        )


@bot.tree.command(
    name="top",
    description="Top pisteet"
)
async def top(interaction: discord.Interaction):

    cursor.execute("""
        SELECT user_id, points, streak
        FROM streaks
        ORDER BY points DESC
        LIMIT 10
    """)

    rows = cursor.fetchall()

    text = "🏆 Top Pisteet\n\n"

    for i, (user_id, points, streak) in enumerate(rows, start=1):

        try:
            user = await bot.fetch_user(user_id)
            name = user.display_name
        except:
            name = str(user_id)

        text += (
            f"{i}. {name} — ⭐ {points} "
            f"(🔥 {streak})\n"
        )

    await interaction.response.send_message(text)


bot.run(TOKEN)
