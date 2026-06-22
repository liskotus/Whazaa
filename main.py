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
    last_post TEXT
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
    today = datetime.utcnow().date()

    cursor.execute(
        "SELECT streak, last_post FROM streaks WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()

    if row is None:

        cursor.execute(
            "INSERT INTO streaks VALUES (?, ?, ?)",
            (user_id, 1, str(today))
        )

        db.commit()

        await message.add_reaction("🔥")

    else:

        streak, last_post = row
        last_post = datetime.strptime(
            last_post,
            "%Y-%m-%d"
        ).date()

        days = (today - last_post).days

        if days == 0:
            pass

        elif days == 1:

            streak += 1

            cursor.execute(
                """
                UPDATE streaks
                SET streak=?, last_post=?
                WHERE user_id=?
                """,
                (streak, str(today), user_id)
            )

            db.commit()

            await message.reply(
                f"🔥 Streak kasvoi! Nyt {streak} päivää putkeen."
            )

        else:

            streak = 1

            cursor.execute(
                """
                UPDATE streaks
                SET streak=?, last_post=?
                WHERE user_id=?
                """,
                (streak, str(today), user_id)
            )

            db.commit()

            await message.reply(
                "💔 Putki katkesi. Aloitit uuden streakin!"
            )

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
    name="top",
    description="Top streakit"
)
async def top(interaction: discord.Interaction):

    cursor.execute("""
        SELECT user_id, streak
        FROM streaks
        ORDER BY streak DESC
        LIMIT 10
    """)

    rows = cursor.fetchall()

    text = "🏆 Top Streakit\n\n"

    for i, (user_id, streak) in enumerate(rows, start=1):

        try:
            user = await bot.fetch_user(user_id)
            name = user.display_name

        except Exception:
            name = str(user_id)

        text += f"{i}. {name} — 🔥 {streak}\n"

    await interaction.response.send_message(text)


bot.run(TOKEN)
