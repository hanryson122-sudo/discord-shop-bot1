import discord
from discord.ext import commands
import re
import os
from threading import Thread
from flask import Flask

# --- RENDER ALIVE CODE ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render automatically sets an environment variable named PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
# -------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

PRICES = {
    "necklace": {"usd": 5.0, "robux": 450},
    "backpacks & purses": {"usd": 4.0, "robux": 350},
    "bows & hairclips": {"usd": 3.0, "robux": 250},
    "beaded": {"usd": 1.0, "robux": 100},
    "jumbo": {"usd": 1.0, "robux": 100},
    "addons": {"usd": 0.0, "robux": 0},
    "charms": {"usd": 0.5, "robux": 50},     
    "fastpass": {"usd": 5.0, "robux": 500},   
    "upload_fee": {"usd": 2.5, "robux": 250} 
}

class FinalizeOrderModal(discord.ui.Modal, title='🛒 Complete Your Order'):
    def __init__(self, selected_items):
        super().__init__()
        self.selected_items = selected_items

        self.quantity = discord.ui.TextInput(
            label='Quantity for each selected catalog item?',
            style=discord.TextStyle.short,
            placeholder='e.g., 1',
            default='1',
            required=True
        )
        self.text_and_font = discord.ui.TextInput(
            label='What text and font would you like?',
            style=discord.TextStyle.paragraph,
            placeholder='e.g., Text: "Hello", Font: Arial / Cursive / Bold...',
            required=True
        )
        self.charm_count = discord.ui.TextInput(
            label='How many Charms would you like to add?',
            style=discord.TextStyle.short,
            placeholder='Type a number (e.g., 0, 3, 5)',
            default='0',
            required=True
        )
        self.fast_pass = discord.ui.TextInput(
            label='Add a Fast Pass? (+$5.00 / 500 Robux)',
            style=discord.TextStyle.short,
            placeholder='Yes or No',
            default='No',
            max_length=3,
            required=True
        )
        self.payment_method = discord.ui.TextInput(
            label='Payment Method?',
            style=discord.TextStyle.short,
            placeholder='USD or Robux',
            required=True
        )

        self.add_item(self.quantity)
        self.add_item(self.text_and_font)
        self.add_item(self.charm_count)
        self.add_item(self.fast_pass)
        self.add_item(self.payment_method)

    async def on_submit(self, interaction: discord.Interaction):
        total_usd = PRICES["upload_fee"]["usd"]
        total_robux = PRICES["upload_fee"]["robux"]
        summary_lines = [f"**Base Upload Fee**\n└ `$2.50` / `250R`"]
        
        qty_input = self.quantity.value.strip().lower()

        for item in self.selected_items:
            if item in PRICES:
                item_qty = 1 
                if qty_input.isdigit():
                    item_qty = int(qty_input)
                else:
                    match = re.search(r'(\d+)\s*' + re.escape(item[:5]), qty_input)
                    if match:
                        item_qty = int(match.group(1))
                
                if item_qty <= 0:
                    item_qty = 1

                item_usd = PRICES[item]["usd"] * item_qty
                item_robux = PRICES[item]["robux"] * item_qty
                total_usd += item_usd
                total_robux += item_robux
                
                if PRICES[item]["usd"] == 0:
                    summary_lines.append(f"**{item.title()}** × {item_qty}\n└ *Free Add-on*")
                else:
                    summary_lines.append(f"**{item.title()}** × {item_qty}\n└ `${item_usd:.2f}` / `{item_robux}R`")

        charm_input = self.charm_count.value.strip().lower()
        charm_digits = re.findall(r'\d+', charm_input)
        if charm_digits:
            charms_qty = int(charm_digits[0])
            if charms_qty > 0:
                charms_usd = PRICES["charms"]["usd"] * charms_qty
                charms_robux = PRICES["charms"]["robux"] * charms_qty
                total_usd += charms_usd
                total_robux += charms_robux
                summary_lines.append(f"**Charms** × {charms_qty}\n└ `${charms_usd:.2f}` / `{charms_robux}R`")

        has_fastpass = self.fast_pass.value.strip().lower() in ['yes', 'y']
        if has_fastpass:
            total_usd += PRICES["fastpass"]["usd"]
            total_robux += PRICES["fastpass"]["robux"]
            summary_lines.append(f"**Fast Pass**\n└ `${PRICES['fastpass']['usd']:.2f}` / `{PRICES['fastpass']['robux']}R`")

        method = self.payment_method.value.strip().upper()
        if "USD" in method or "$" in method:
            final_cost = f"${total_usd:.2f} USD"
        elif "ROBUX" in method or "R$" in method or "R" in method:
            final_cost = f"{total_robux} Robux"
        else:
            final_cost = f"${total_usd:.2f} USD / {total_robux} Robux"

        embed = discord.Embed(
            title="🛍️ New Order Submitted",
            description=f"A new custom order request has been logged by {interaction.user.mention}.",
            color=discord.Color.brand_green()
        )
        embed.add_field(name="📋 Order Items & Breakdown", value="\n".join(summary_lines) if summary_lines else "None", inline=False)
        embed.add_field(name="🎨 Text & Font Style Choice", value=f"{self.text_and_font.value}", inline=False)
        embed.add_field(name="💳 Payment Preference", value=f"`{method}`", inline=True)
        embed.add_field(name="📦 Base Quantities", value=f"`{self.quantity.value}`", inline=True)
        embed.add_field(name="💰 Total Calculated Invoice", value=f"**{final_cost}**", inline=False)
        embed.set_footer(text="Shop Order Management System")

        await interaction.response.send_message(content="📌 <@1547080861466230804> <@1556416945283399750> please assist!", embed=embed)

class MultiItemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name.title(), value=name, description="✨ FREE ADD-ON" if data['usd'] == 0 else f"${data['usd']:.2f} USD / {data['robux']}R")
            for name, data in PRICES.items() if name not in ["fastpass", "charms", "upload_fee"]
        ]
        super().__init__(placeholder="Step 1: Check the boxes for the items you want...", min_values=1, max_values=len(options), options=options, custom_id="persistent_multi_select")

    async def callback(self, interaction: discord.Interaction):
        if not hasattr(self.view, 'user_selections'):
            self.view.user_selections = {}
        self.view.user_selections[interaction.user.id] = self.values
        await interaction.response.send_message("✅ Items saved to your session! Click 'Confirm Order Selection' to complete the form.", ephemeral=True)

class OrderSystemView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.user_selections = {}
        self.add_item(MultiItemSelect())

    @discord.ui.button(label="Confirm Order Selection", style=discord.ButtonStyle.green, row=1, custom_id="persistent_confirm_btn")
    async def confirm_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_items = self.user_selections.get(interaction.user.id, [])
        if not user_items:
            await interaction.response.send_message("❌ Please select at least one item from the checkbox dropdown menu first!", ephemeral=True)
            return
        await interaction.response.send_modal(FinalizeOrderModal(user_items))

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🛍️ Shop Catalog & Official Pricing Menu",
        description="Welcome! Check the boxes for all items you wish to buy from the dropdown menu, then click **Confirm Order Selection** below.\n\n⚠️ *Note: Every order automatically includes a flat **$2.50 / 250R** base upload fee.*",
        color=discord.Color.blurple()
    )
    embed.add_field(name="🏷️ Necklaces", value="`450R` or `$5.00 USD`", inline=True)
    embed.add_field(name="🎒 Backpacks & Purses", value="`350R` or `$4.00 USD`", inline=True)
    embed.add_field(name="🎀 Bows & Hairclips", value="`250R` or `$3.00 USD`", inline=True)
    embed.add_field(name="📿 Anything Beaded", value="`100R` or `$1.00 USD`", inline=True)
    embed.add_field(name="🧸 Jumbo Items", value="`100R` or `$1.00 USD`", inline=True)
    embed.add_field(name="🎁 Addons", value="**FREE**", inline=True)
    embed.add_field(name="✨ Extra Charms", value="`50R` or `$0.50 USD ca` *(Configured in form)*", inline=False)
    embed.set_footer(text="Select your items and click confirm below.")
    await ctx.send(embed=embed, view=OrderSystemView())

# Start background web server, then launch bot using secure token lookups
keep_alive()
bot.run(os.environ.get('MTU2NzA3MDIyNzg2NTI3NjQ1OA.GzIJIG.UAMRY9h_20RjJxP1HSV0b7CUP12SDUAbs7V-dM'))
