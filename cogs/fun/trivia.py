"""
Trivia command using Open Trivia Database API
"""
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import html


class TriviaButton(discord.ui.Button):
    """Button for trivia answers"""
    def __init__(self, label: str, is_correct: bool, custom_id: str):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id=custom_id
        )
        self.is_correct = is_correct
    
    async def callback(self, interaction: discord.Interaction):
        # Check if the person clicking is the one who started the trivia
        if interaction.user.id != self.view.user_id:
            await interaction.response.send_message("❌ This isn't your trivia question!", ephemeral=True)
            return
        
        # Disable all buttons after answer
        for item in self.view.children:
            item.disabled = True
        
        if self.is_correct:
            # Correct answer
            self.style = discord.ButtonStyle.success
            embed = self.view.message.embeds[0]
            embed.color = discord.Color.green()
            embed.add_field(name="Result", value=f"✅ **Correct!** Well done, {interaction.user.mention}!", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            # Wrong answer
            self.style = discord.ButtonStyle.danger
            
            # Highlight the correct answer
            for item in self.view.children:
                if isinstance(item, TriviaButton) and item.is_correct:
                    item.style = discord.ButtonStyle.success
            
            embed = self.view.message.embeds[0]
            embed.color = discord.Color.red()
            embed.add_field(name="Result", value=f"❌ **Wrong!** The correct answer was: **{self.view.correct_answer}**", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=self.view)


class TriviaView(discord.ui.View):
    """View containing trivia answer buttons"""
    def __init__(self, question_data: dict, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.correct_answer = html.unescape(question_data['correct_answer'])
        self.message = None
        
        # Combine and shuffle answers
        all_answers = [self.correct_answer] + [html.unescape(ans) for ans in question_data['incorrect_answers']]
        random.shuffle(all_answers)
        
        # Create buttons for each answer
        for i, answer in enumerate(all_answers):
            is_correct = (answer == self.correct_answer)
            label = answer
            if len(label) > 80:
                label = label[:77] + "..."
            
            button = TriviaButton(
                label=label,
                is_correct=is_correct,
                custom_id=f"trivia_{i}"
            )
            self.add_item(button)
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in view interactions"""
        import logging
        logger = logging.getLogger('Lilith.TriviaView')
        logger.error(f"Error in TriviaView: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing this action.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred processing this action.", ephemeral=True)
        except:
            pass
    
    async def on_timeout(self):
        """Called when the view times out"""
        for item in self.children:
            item.disabled = True
            if isinstance(item, TriviaButton) and item.is_correct:
                item.style = discord.ButtonStyle.success
        
        if self.message:
            try:
                embed = self.message.embeds[0]
                embed.color = discord.Color.orange()
                embed.add_field(name="Result", value=f"⏰ **Time's up!** The correct answer was: **{self.correct_answer}**", inline=False)
                await self.message.edit(embed=embed, view=self)
            except:
                pass


class Trivia(commands.Cog):
    """Trivia quiz commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://opentdb.com/api.php"
    
    @app_commands.command(name="trivia", description="Answer a random trivia question!")
    @app_commands.describe(
        difficulty="Choose difficulty level",
        category="Choose a category (optional)"
    )
    @app_commands.choices(difficulty=[
        app_commands.Choice(name="Easy", value="easy"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Hard", value="hard"),
        app_commands.Choice(name="Random", value="random")
    ])
    @app_commands.choices(category=[
        app_commands.Choice(name="Any Category", value="any"),
        app_commands.Choice(name="General Knowledge", value="9"),
        app_commands.Choice(name="Books", value="10"),
        app_commands.Choice(name="Film", value="11"),
        app_commands.Choice(name="Music", value="12"),
        app_commands.Choice(name="Video Games", value="15"),
        app_commands.Choice(name="Science & Nature", value="17"),
        app_commands.Choice(name="Computers", value="18"),
        app_commands.Choice(name="Mathematics", value="19"),
        app_commands.Choice(name="Sports", value="21"),
        app_commands.Choice(name="Geography", value="22"),
        app_commands.Choice(name="History", value="23"),
        app_commands.Choice(name="Animals", value="27"),
        app_commands.Choice(name="Vehicles", value="28"),
        app_commands.Choice(name="Comics", value="29"),
        app_commands.Choice(name="Anime & Manga", value="31"),
    ])
    async def trivia(
        self, 
        interaction: discord.Interaction, 
        difficulty: app_commands.Choice[str] = None,
        category: app_commands.Choice[str] = None
    ):
        """Start a trivia question"""
        await interaction.response.defer()
        
        # Build API parameters
        params = {"amount": 1, "type": "multiple"}
        
        if difficulty and difficulty.value != "random":
            params["difficulty"] = difficulty.value
        
        if category and category.value != "any":
            params["category"] = category.value
        
        try:
            # Fetch trivia question
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url, params=params) as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Failed to fetch trivia question. Try again!", ephemeral=True)
                        return
                    
                    data = await response.json()
                    
                    if data['response_code'] != 0 or not data['results']:
                        await interaction.followup.send("❌ No trivia questions available for these settings!", ephemeral=True)
                        return
                    
                    question_data = data['results'][0]
            
            # Decode HTML entities
            question = html.unescape(question_data['question'])
            category_name = html.unescape(question_data['category'])
            difficulty_level = question_data['difficulty'].capitalize()
            
            # Create embed
            embed = discord.Embed(
                title="🎯 Trivia Question",
                description=f"**{question}**",
                color=discord.Color.blue()
            )
            embed.add_field(name="Category", value=category_name, inline=True)
            embed.add_field(name="Difficulty", value=difficulty_level, inline=True)
            embed.set_footer(text=f"Asked by {interaction.user.display_name} • You have 30 seconds to answer!")
            
            # Create view with buttons
            view = TriviaView(question_data, interaction.user.id)
            
            # Send message
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = message
            
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}", ephemeral=True)


    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        import logging
        logger = logging.getLogger('Lilith.Trivia')
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in trivia command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Trivia(bot))
