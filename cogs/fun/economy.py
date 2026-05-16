"""
Economy commands cog - Balance management, daily rewards, transfers, work system
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger('Lilith.Economy')
from .economy_utils import (
    get_balance, set_balance, add_balance, remove_balance, force_remove_balance,
    has_balance, get_last_daily, set_last_daily, get_leaderboard,
    get_user_stats, CURRENCY_NAME, STARTING_BALANCE
)


class Economy(commands.Cog):
    """Economy management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="balance", description="Check your balance")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        """Check balance for yourself or another user"""
        target = user or interaction.user
        balance = await get_balance(target.id)
        stats = await get_user_stats(target.id)
        
        embed = discord.Embed(
            title=f"💰 {target.display_name}'s Balance",
            color=discord.Color.gold()
        )
        embed.add_field(name="Current Balance", value=f"**{balance:,}** {CURRENCY_NAME}", inline=False)
        embed.add_field(name="Total Earned", value=f"{stats['total_earned']:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Total Spent", value=f"{stats['total_spent']:,} {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Net Profit", value=f"{stats['net_profit']:,} {CURRENCY_NAME}", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily reward (100-300 mayem)"""
        user_id = interaction.user.id
        last_daily = await get_last_daily(user_id)
        now = datetime.utcnow()
        
        # Check if user can claim
        if last_daily:
            last_claim = datetime.fromisoformat(last_daily)
            time_since = now - last_claim
            
            if time_since < timedelta(hours=24):
                # Calculate time remaining
                time_left = timedelta(hours=24) - time_since
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                
                embed = discord.Embed(
                    title="⏰ Daily Reward",
                    description=f"You've already claimed your daily reward!\n\n**Come back in:** {hours}h {minutes}m",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Give reward
        reward = random.randint(100, 300)
        new_balance = await add_balance(user_id, reward)
        await set_last_daily(user_id, now.isoformat())
        
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You received **{reward}** {CURRENCY_NAME}!",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}")
        embed.set_footer(text="Come back in 24 hours for another reward!")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="give", description="Give mayem to another user")
    @app_commands.describe(user="User to give mayem to", amount="Amount to give")
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Transfer currency to another user"""
        # Validation
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't give mayem to yourself!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.response.send_message("❌ You can't give mayem to bots!", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Transfer
        await remove_balance(interaction.user.id, amount)
        new_balance = await add_balance(user.id, amount)
        
        embed = discord.Embed(
            title="💸 Transfer Successful",
            description=f"{interaction.user.mention} gave **{amount:,}** {CURRENCY_NAME} to {user.mention}!",
            color=discord.Color.green()
        )
        embed.add_field(name=f"{user.display_name}'s New Balance", value=f"{new_balance:,} {CURRENCY_NAME}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="View the richest users")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show top 10 users by balance"""
        await interaction.response.defer()
        
        top_users = await get_leaderboard(10)
        
        if not top_users:
            await interaction.followup.send("No users found!")
            return
        
        embed = discord.Embed(
            title="🏆 Mayem Leaderboard",
            description="Top 10 richest users",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (user_id, data) in enumerate(top_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                medal = medals[i-1] if i <= 3 else f"**{i}.**"
                embed.add_field(
                    name=f"{medal} {user.display_name}",
                    value=f"{data['balance']:,} {CURRENCY_NAME}",
                    inline=False
                )
            except:
                continue
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="work", description="Work to earn cursed coins")
    @app_commands.checks.cooldown(1, 3600, key=lambda i: i.user.id) # 1 hour cooldown
    async def work(self, interaction: discord.Interaction):
        """Work for random amount of cursed coins (50-200)"""
        jobs = [
            ("mowed lawns", 50, 150),
            ("delivered packages", 60, 140),
            ("washed cars", 40, 120),
            ("walked dogs", 45, 130),
            ("cleaned houses", 70, 180),
            ("fixed computers", 80, 200),
            ("taught a class", 90, 200),
            ("painted a fence", 55, 145),
            ("sold lemonade", 30, 100),
            ("did yard work", 50, 140),
            ("babysat kids", 60, 160),
            ("cooked meals", 65, 155),
            ("organized files", 50, 130),
            ("built furniture", 75, 190),
            ("repaired bikes", 55, 145)
        ]
        
        job_name, min_pay, max_pay = random.choice(jobs)
        earnings = random.randint(min_pay, max_pay)
        
        new_balance = await add_balance(interaction.user.id, earnings)
        
        embed = discord.Embed(
            title="💼 Work Complete!",
            description=f"You {job_name} and earned **{earnings}** {CURRENCY_NAME}!",
            color=0xF1C40F # Premium Gold
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="New Balance", value=f"💰 **{new_balance:,}** {CURRENCY_NAME}")
        embed.set_footer(text="Keep it up! ⚡")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="crime", description="Commit a crime for cursed coins (risky!)")
    @app_commands.checks.cooldown(1, 7200, key=lambda i: i.user.id) # 2 hours cooldown
    async def crime(self, interaction: discord.Interaction):
        """Commit a crime - high risk, high reward"""
        crimes = [
            ("robbed a bank", 200, 500, 100, 300),
            ("stole a car", 150, 400, 80, 250),
            ("hacked a system", 180, 450, 90, 280),
            ("smuggled goods", 160, 420, 85, 260),
            ("pickpocketed someone", 100, 300, 50, 200),
            ("broke into a house", 140, 380, 70, 240),
            ("scammed someone", 120, 350, 60, 220),
            ("sold fake tickets", 110, 320, 55, 210)
        ]
        
        crime_name, min_reward, max_reward, min_fine, max_fine = random.choice(crimes)
        success = random.random() > 0.4  # 60% success rate
        
        if success:
            earnings = random.randint(min_reward, max_reward)
            new_balance = await add_balance(interaction.user.id, earnings)
            
            embed = discord.Embed(
                title="😈 Crime Successful!",
                description=f"You {crime_name} and got away with **{earnings}** {CURRENCY_NAME}!",
                color=0x2ECC71 # Premium Green
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.add_field(name="New Balance", value=f"💰 **{new_balance:,}** {CURRENCY_NAME}")
        else:
            fine = random.randint(min_fine, max_fine)
            new_balance = await force_remove_balance(interaction.user.id, fine)
            
            balance_display = f"{'🔴 ' if new_balance < 0 else '💰 '}**{new_balance:,}** {CURRENCY_NAME}"
            
            embed = discord.Embed(
                title="🚔 Caught!",
                description=f"You tried to {crime_name.split()[0]} but got caught!\n\nYou were fined **{fine:,}** {CURRENCY_NAME}.",
                color=0xE74C3C # Premium Red
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.add_field(name="New Balance", value=balance_display)
            if new_balance < 0:
                embed.set_footer(text="⚠️ You're in debt! Earn some coins to get back in the green.")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="beg", description="Beg for mayem")
    @app_commands.checks.cooldown(1, 14400, key=lambda i: i.user.id) # 4 hours cooldown
    async def beg(self, interaction: discord.Interaction):
        """Beg for a small amount of mayem"""
        # 70% chance of success
        if random.random() > 0.3:
            earnings = random.randint(10, 50)
            new_balance = await add_balance(interaction.user.id, earnings)
            
            responses = [
                f"A kind stranger gave you **{earnings}** {CURRENCY_NAME}!",
                f"Someone felt bad and tossed you **{earnings}** {CURRENCY_NAME}!",
                f"You found **{earnings}** {CURRENCY_NAME} on the ground!",
                f"A generous person donated **{earnings}** {CURRENCY_NAME}!",
                f"Someone's pocket had a hole, you got **{earnings}** {CURRENCY_NAME}!"
            ]
            
            embed = discord.Embed(
                title="🙏 Begging Successful",
                description=random.choice(responses),
                color=discord.Color.green()
            )
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}")
        else:
            responses = [
                "Everyone ignored you...",
                "Someone told you to get a job!",
                "People walked past without looking...",
                "A dog barked at you...",
                "You got nothing but dirty looks..."
            ]
            
            embed = discord.Embed(
                title="🙏 No Luck",
                description=random.choice(responses),
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="setbalance", description="Set a user's balance (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="User to set balance for", amount="New balance amount")
    async def setbalance(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Admin command to set user balance (can be negative)"""
        await set_balance(user.id, amount)
        
        embed = discord.Embed(
            title="⚙️ Balance Updated",
            description=f"Set {user.mention}'s balance to **{amount:,}** {CURRENCY_NAME}",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in economy command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))
