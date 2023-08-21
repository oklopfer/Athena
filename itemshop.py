import json
import logging
import math
import discord
from discord.ext import commands
from math import ceil
from sys import exit
from time import sleep
from datetime import datetime

import coloredlogs
from PIL import Image, ImageDraw

from util import ImageUtil, Utility

log = logging.getLogger(__name__)
coloredlogs.install(level="INFO", fmt="[%(asctime)s] %(message)s", datefmt="%I:%M:%S")

import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)

intents = discord.Intents.default()  # Use default intents
intents.message_content = True       # Enable the MESSAGE_CONTENT intent (if you need to read message content)
intents.messages = True              # Enable the MESSAGES intent (if you need to receive message events)

bot = commands.Bot(command_prefix='!', intents=intents)
TOKEN = #'TOKEN_ID'
CHANNEL_ID = #CHANNEL_ID

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        current_date = datetime.utcnow().strftime('%B %d, %Y')
        with open('itemshop.png', 'rb') as img:
            await channel.send(f"Daily Item Shop {current_date}:", file=discord.File(img, 'itemshop.png'))
            await bot.close()

@bot.command()
async def upload(ctx):
    current_date = datetime.utcnow().strftime('%B %d, %Y')
    with open('itemshop.png', 'rb') as img:
        await ctx.send(f"Daily Item Shop {current_date}:", file=discord.File(img, 'itemshop.png'))
        await bot.close()

class Athena:
    """Fortnite Item Shop Generator."""

    def main(self):
        print("Fortnite Item Shop Generator")

        initialized = Athena.LoadConfiguration(self)

        if initialized is True:
            if self.delay > 0:
                log.info(f"Delaying process start for {self.delay}s...")
                sleep(self.delay)

            itemShop = Utility.GET(
                self,
                "https://fortnite-api.com/v2/shop/br/combined",
                {"language": self.language},
            )

            if itemShop is not None:
                itemShop = json.loads(itemShop)["data"]

                # Strip time from the timestamp, we only need the date
                date = Utility.ISOtoHuman(
                    self, itemShop["date"].split("T")[0], self.language
                )
                log.info(f"Retrieved Item Shop for {date}")

                shopImage = Athena.GenerateImage(self, date, itemShop)

    def add_yellow_border(card, border_size=10):
        """Add a yellow border around an image."""
        draw = ImageDraw.Draw(card)
        width, height = card.size
        # Top border
        draw.rectangle([0, 0, width, border_size], fill='yellow')
        # Bottom border
        draw.rectangle([0, height - border_size, width, height], fill='yellow')
        # Left border
        draw.rectangle([0, 0, border_size, height], fill='yellow')
        # Right border
        draw.rectangle([width - border_size, 0, width, height], fill='yellow')
        return card

    def LoadConfiguration(self):
        """
        Set the configuration values specified in configuration.json
        
        Return True if configuration sucessfully loaded.
        """

        configuration = json.loads(Utility.ReadFile(self, "configuration", "json"))

        try:
            self.delay = configuration["delayStart"]
            self.language = configuration["language"]

            log.info("Loaded configuration")

            return True
        except Exception as e:
            log.critical(f"Failed to load configuration, {e}")

    def GenerateImage(self, date: str, itemShop: dict):
        """
        Generate the Item Shop image using the provided Item Shop.

        Return True if image sucessfully saved.
        """

        try:
            featured = itemShop["featured"]["entries"]
            daily = itemShop["daily"]["entries"]

            # Ensure both Featured and Daily have at least 1 item
            if (len(featured) <= 0) or (len(daily) <= 0):
                raise Exception(f"Featured: {len(featured)}, Daily: {len(daily)}")
        except Exception as e:
            log.critical(f"Failed to parse Item Shop Featured and Daily items, {e}")

            return False

        all_items = featured + daily
        all_items.sort(key=lambda x: x["section"]["index"])
        rows = max(0, ceil(len(all_items) / 6))
        columns = math.ceil(math.sqrt(len(all_items)))
        max_items_per_row = columns + 2
        num_items = len(all_items)
        if num_items <= 6:
            width = 320 * num_items
        else:
            width = 320 * max_items_per_row
        shopImage = Image.new("RGBA", (width, (545 * (columns - 1) + 340) - 455))

        try:
            background = ImageUtil.Open(self, "background.png")
            background = ImageUtil.RatioResize(
                self, background, shopImage.width, shopImage.height
            )
            shopImage.paste(
                background, ImageUtil.CenterX(self, background.width, shopImage.width)
            )
        except FileNotFoundError:
            log.warn("Failed to open background.png, defaulting to dark gray")
            shopImage.paste((18, 18, 18), [0, 0, shopImage.size[0], shopImage.size[1]])

        logo = ImageUtil.Open(self, "logo.png")
        logo = ImageUtil.RatioResize(self, logo, 0, 210)
        shopImage.paste(
            logo, ImageUtil.CenterX(self, logo.width, shopImage.width, 20), logo
        )

        canvas = ImageDraw.Draw(shopImage)
        font = ImageUtil.Font(self, 48)
        textWidth, _ = font.getsize(date)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, shopImage.width, 255),
            date,
            (255, 255, 255),
            font=font,
        )

        # Track grid position
        i = 0

        for item in all_items:
            card = Athena.GenerateCard(self, item)

            if card is not None:

                shopImage.paste(
                    card,
                    (
                        ((max_items_per_row * 8) + ((i % max_items_per_row) * (card.width + 5))),
                        355 + ((i // max_items_per_row) * (card.height + 5)),
                    ),
                    card,
                )

                i += 1

        try:
            shopImage.save("itemshop.png")
            log.info("Generated Item Shop image")

            return True
        except Exception as e:
            log.critical(f"Failed to save Item Shop image, {e}")

    def GenerateCard(self, item: dict):
        """Return the card image for the provided Fortnite Item Shop item."""

        try:
            if "bundle" in item and item["bundle"] is not None:
                name = item["bundle"]["name"]
                icon = item["bundle"]["image"]
                shop_time = "Bundle"
            else:
                name = item["items"][0]["name"]
                if isinstance(item["items"][0]["images"]["featured"], dict):
                    icon = item["items"][0]["images"]["featured"]
                else:
                    icon = item["items"][0]["images"]["icon"]
                shopHistory = item["items"][0]["shopHistory"]
                shopHistory_dates = [datetime.fromisoformat(date_string) for date_string in shopHistory]
                if len(shopHistory_dates) < 2:
                    shop_time = "New!"
                else:
                    days_difference = (shopHistory_dates[-1] - shopHistory_dates[-2]).days
                    if days_difference == 1:
                        shop_time = f"{days_difference} day"
                    else:
                        shop_time = f"{days_difference} days"
            rarity = item["items"][0]["rarity"]["value"]
            category = item["items"][0]["type"]["value"]
            price = item["finalPrice"]
        except Exception as e:
            log.error(f"Failed to parse item {name} ({rarity}/{category}/{price}), {e}")

            return

        if rarity == "frozen":
            blendColor = (148, 223, 255)
        elif rarity == "lava":
            blendColor = (234, 141, 35)
        elif rarity == "legendary":
            blendColor = (211, 120, 65)
        elif rarity == "dark":
            blendColor = (251, 34, 223)
        elif rarity == "starwars":
            blendColor = (231, 196, 19)
        elif rarity == "marvel":
            blendColor = (197, 51, 52)
        elif rarity == "dc":
            blendColor = (84, 117, 199)
        elif rarity == "icon":
            blendColor = (54, 183, 183)
        elif rarity == "shadow":
            blendColor = (113, 113, 113)
        elif rarity == "epic":
            blendColor = (177, 91, 226)
        elif rarity == "rare":
            blendColor = (73, 172, 242)
        elif rarity == "uncommon":
            blendColor = (96, 170, 58)
        elif rarity == "common":
            blendColor = (190, 190, 190)
        else:
            blendColor = (255, 255, 255)

        card = Image.new("RGBA", (300, 545))

        try:
            layer = ImageUtil.Open(self, f"card_top_{rarity}.png")
        except FileNotFoundError:
            log.warn(f"Failed to open card_top_{rarity}.png, defaulted to Common")
            layer = ImageUtil.Open(self, "card_top_common.png")

        card.paste(layer)

        icon = ImageUtil.Download(self, icon)
        if (category == "outfit") or (category == "emote"):
            icon = ImageUtil.RatioResize(self, icon, 285, 365)
        elif category == "wrap":
            icon = ImageUtil.RatioResize(self, icon, 230, 310)
        else:
            icon = ImageUtil.RatioResize(self, icon, 310, 390)
        if (category == "outfit"):
            if icon.mode == "RGBA":
                alpha = icon.split()[3]
            else:
                alpha = None
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width), mask=alpha)
        elif (category == "emote"):
            if icon.mode == "RGBA":
                r, g, b, alpha = icon.split()
                combined_icon = Image.merge("RGBA", (r, g, b, alpha))
                card.paste(combined_icon, ImageUtil.CenterX(self, icon.width, card.width, 15), mask=alpha)
            else:
                card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), icon)
        else:
            if icon.mode == "RGBA":
                alpha = icon.split()[3]
            else:
                alpha = None
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), mask=alpha)

        if len(item["items"]) > 1:
            # Track grid position
            i = 0

            # Start at position 1 in items array
            for extra in item["items"][1:]:
                try:
                    extraRarity = extra["rarity"]["value"]
                    extraIcon = extra["images"]["smallIcon"]
                except Exception as e:
                    log.error(f"Failed to parse item {name}, {e}")

                    return

                try:
                    layer = ImageUtil.Open(self, f"box_bottom_{extraRarity}.png")
                except FileNotFoundError:
                    log.warn(
                        f"Failed to open box_bottom_{extraRarity}.png, defaulted to Common"
                    )
                    layer = ImageUtil.Open(self, "box_bottom_common.png")

                card.paste(
                    layer,
                    (
                        (card.width - (layer.width + 9)),
                        (9 + ((i // 1) * (layer.height))),
                    ),
                )

                extraIcon = ImageUtil.Download(self, extraIcon)
                extraIcon = ImageUtil.RatioResize(self, extraIcon, 75, 75)

                card.paste(
                    extraIcon,
                    (
                        (card.width - (layer.width + 9)),
                        (9 + ((i // 1) * (extraIcon.height))),
                    ),
                    extraIcon,
                )

                try:
                    layer = ImageUtil.Open(self, f"box_faceplate_{extraRarity}.png")
                except FileNotFoundError:
                    log.warn(
                        f"Failed to open box_faceplate_{extraRarity}.png, defaulted to Common"
                    )
                    layer = ImageUtil.Open(self, "box_faceplate_common.png")

                card.paste(
                    layer,
                    (
                        (card.width - (layer.width + 9)),
                        (9 + ((i // 1) * (layer.height))),
                    ),
                    layer,
                )

                i += 1

        try:
            layer = ImageUtil.Open(self, f"card_faceplate_{rarity}.png")
        except FileNotFoundError:
            log.warn(f"Failed to open card_faceplate_{rarity}.png, defaulted to Common")
            layer = ImageUtil.Open(self, "card_faceplate_common.png")

        card.paste(layer, layer)

        try:
            layer = ImageUtil.Open(self, f"card_bottom_{rarity}.png")
        except FileNotFoundError:
            log.warn(f"Failed to open card_bottom_{rarity}.png, defaulted to Common")
            layer = ImageUtil.Open(self, "card_bottom_common.png")

        card.paste(layer, layer)

        canvas = ImageDraw.Draw(card)

        font = ImageUtil.Font(self, 30)
        textWidth, _ = font.getsize(f"{rarity.capitalize()} {category.capitalize()}")
        canvas.text(
            ImageUtil.CenterX(self, textWidth, card.width, 385),
            f"{rarity.capitalize()} {category.capitalize()}",
            blendColor,
            font=font,
        )

        vbucks = ImageUtil.Open(self, "vbucks.png")
        vbucks = ImageUtil.RatioResize(self, vbucks, 25, 25)

        price = str(f"{price:,}")
        textWidth, _ = font.getsize(price)
        canvas.text(
            ImageUtil.CenterX(self, ((textWidth - 5) - vbucks.width), (card.width - 175), 495),
            price,
            blendColor,
            font=font,
        )

        card.paste(
            vbucks,
            ImageUtil.CenterX(self, (vbucks.width + (textWidth + 5)), (card.width - 175), 495),
            vbucks,
        )

        textWidth, _ = font.getsize(shop_time)
        canvas.text(
            ImageUtil.CenterX(self, ((textWidth - 5)), (card.width + 140), 495),
            shop_time,
            blendColor,
            font=font,
        )
        if shop_time == "New!":
            card = self.add_yellow_border(card)

        font = ImageUtil.Font(self, 56)
        textWidth, _ = font.getsize(name)
        change = 0
        if textWidth >= 270:
            # Ensure that the item name does not overflow
            font, textWidth, change = ImageUtil.FitTextX(self, name, 56, 260)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, card.width, (425 + (change / 2))),
            name,
            (255, 255, 255),
            font=font,
        )

        return card


if __name__ == "__main__":
    try:
        Athena.main(Athena)
        bot.run(TOKEN)
    except KeyboardInterrupt:
        log.info("Exiting...")
        exit()
