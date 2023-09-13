from discord import ButtonStyle
from discord.ui import Button


def change(button: Button, result: int):
    if result == 1:
        button.emoji = "✅"
        button.label = ""  # "Success"
        button.style = ButtonStyle.success
        button.disabled = True

    if result == 0:
        button.emoji = "⌛"
        button.label = ""  # "Loading..."
        button.style = ButtonStyle.secondary
        button.disabled = True

    if result == -1:
        button.emoji = "🔄"
        button.label = ""  # "Try again"
        button.style = ButtonStyle.danger
        button.disabled = False
