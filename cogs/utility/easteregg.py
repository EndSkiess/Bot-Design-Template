import discord
from discord import app_commands
from discord.ext import commands
from cogs.fun.economy_utils import add_balance, CURRENCY_NAME
from cogs.utils.ravendb_manager import raven_db
from cogs.utils.seed_codes import seed_codes_if_needed

CODES_DOC_ID = "easteregg/codes"

class EasterEgg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # ==========================================
        # CONFIGURATION - CHANGE THESE TO MATCH YOURS!
        # ==========================================
        self.reward_role_name = "[SA] System Admin" # The role to give them exactly as it's spelled
        self.hall_of_fame_channel_id = 1485216901637607504 # Change this to a channel ID like: 123456789012345678
        self.reward_amount = 10000 # How many coins to give them
        self.discount_code = "SKIES-10%-OFF" # The real-life discount code
        # ==========================================
        
        self.db_doc_id = "easteregg/redeemed"

    @commands.Cog.listener()
    async def on_ready(self):
        """Seed the 100 codes into RavenDB when the bot starts (only if needed)."""
        await seed_codes_if_needed()

    async def get_redeemed_users(self):
        """Fetch the list of users who already claimed the prize from RavenDB"""
        data = await raven_db.load_document(self.db_doc_id)
        if not data:
            return []
        return data.get("users", [])

    async def add_redeemed_user(self, user_id):
        """Save a user to RavenDB so they can't claim it twice"""
        data = await raven_db.load_document(self.db_doc_id)
        if not data:
            data = {"users": []}
        if user_id not in data["users"]:
            data["users"].append(user_id)
        await raven_db.save_document(self.db_doc_id, data)

    @app_commands.command(name="redeem", description="Redeem a secret access code from the terminal.")
    async def redeem(self, interaction: discord.Interaction, code: str):
        # 1. Prevent double claiming
        redeemed_users = await self.get_redeemed_users()
        if interaction.user.id in redeemed_users:
            await interaction.response.send_message("❌ **ERR:** You have already claimed this prize, Agent.", ephemeral=True)
            return

        # 2. Check the code against the RavenDB code pool
        user_code = code.strip().upper()
        codes_data = await raven_db.load_document(CODES_DOC_ID)
        code_list = codes_data.get("codes", []) if codes_data and isinstance(codes_data, dict) else []

        # Find the matching unused entry
        matched_index = None
        for i, entry in enumerate(code_list):
            if isinstance(entry, dict) and entry.get("code") == user_code and not entry.get("used", True):
                matched_index = i
                break

        if matched_index is not None:
            # Mark the code as used
            code_list[matched_index]["used"] = True
            try:
                await raven_db.save_document(CODES_DOC_ID, {"codes": code_list})
            except Exception as e:
                print(f"Error marking code as used: {e}")
            
            # Save to Database immediately
            await self.add_redeemed_user(interaction.user.id)
            
            # FEATURE 1: Add Economy Balance
            await add_balance(interaction.user.id, self.reward_amount)
            
            # FEATURE 2: Give Role
            role_given = False
            if interaction.guild: # Ensure we are in a server, not DMs
                role = discord.utils.get(interaction.guild.roles, name=self.reward_role_name)
                if role:
                    try:
                        await interaction.user.add_roles(role)
                        role_given = True
                    except discord.Forbidden:
                        print(f"I need 'Manage Roles' permission and my role must be higher than '{self.reward_role_name}'!")
            
            # FEATURE 3: Ephemeral DM / Message with Discount
            response_msg = (
                "<:success:1485218221807108167> **SYSTEM OVERRIDE SUCCESSFUL.**\n\n"
                f"Impressive work finding the terminal, Agent. I have transferred **{self.reward_amount} {CURRENCY_NAME}** to your account.\n"
            )
            
            if role_given:
                response_msg += f"You have been granted the `{self.reward_role_name}` access level.\n"
                
            response_msg += (
                f"\nHere is your exclusive commission discount code: `{self.discount_code}`.\n"
                "Keep this secure."
            )
            
            await interaction.response.send_message(response_msg, ephemeral=True)
            
            # FEATURE 4: Hall of Fame Announcement
            if self.hall_of_fame_channel_id:
                channel = self.bot.get_channel(self.hall_of_fame_channel_id)
                if channel:
                    await channel.send(
                        f"🚨 **MAINFRAME BREACHED** 🚨\n"
                        f"{interaction.user.mention} has successfully bypassed the terminal and claimed the secret prize! Welcome to the elite ranks."
                    )
        else:
            await interaction.response.send_message("❌ **ERR:** INVALID_ACCESS_CODE. Connection closed.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EasterEgg(bot))
