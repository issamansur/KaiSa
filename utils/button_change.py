from discord import ButtonStyle
from discord.ui import Button


def change(button: Button, result: int):
    if result == 1:
        # "Success"
        button.emoji = "✅"
        # button.label = ""
        button.style = ButtonStyle.success
        button.disabled = True

    if result == 0:
        # "Loading..."
        button.emoji = "⌛"
        # button.label = ""
        button.style = ButtonStyle.secondary
        button.disabled = True

    if result == -1:
        # "Try again"
        button.emoji = "🔄"
        # button.label = ""
        button.style = ButtonStyle.danger
        button.disabled = False
