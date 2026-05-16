
import discord
from discord import app_commands

def has_permissions(**perms):
    """
    Custom decorator replacing app_commands.checks.has_permissions.
    Owner/Superusers NO LONGER bypass permissions.
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        # Standard Check
        permissions = interaction.permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise app_commands.MissingPermissions(missing)

    return app_commands.check(predicate)
