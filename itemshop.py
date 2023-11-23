import json
import logging
import math
import discord
import praw
from discord.ext import commands
from math import ceil
from sys import exit
from time import sleep
from datetime import datetime
from multiprocessing import Pool
from functools import partial

import coloredlogs
from PIL import Image, ImageDraw

from util import ImageUtil, Utility

log = logging.getLogger(__name__)
coloredlogs.install(level="INFO", fmt="[%(asctime)s] %(message)s", datefmt="%I:%M:%S")

import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)

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
                intents = discord.Intents.default()  # Use default intents
                intents.message_content = True       # Enable the MESSAGE_CONTENT intent (if you need to read message content)
                intents.messages = True              # Enable the MESSAGES intent (if you need to receive message events)

                bot = commands.Bot(command_prefix='!', intents=intents)

                TOKEN = self.token # should be a string, with quotes
                CHANNEL_ID = self.channel # should be an integer, no quotes

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

                reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    username=self.username,
                    password=self.password
                )

                print(reddit.read_only)
                # Output: False
                
                formatted_date = datetime.utcnow().strftime('%Y-%m-%d')
                self.title = f"Daily Item Shop and Purchase Advice Megathread ({formatted_date})"
                self.image_path = "itemshop.png"

                if self.discordon is True:
                    bot.run(TOKEN)

                if self.redditon is True:
                    reddit.subreddit(self.sub_reddit).submit_image(title=self.title, image_path=self.image_path, flair_id=self.flair_id)

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
            self.discordon = configuration["discord"]["enabled"]
            self.token = configuration["discord"]["TOKEN"]
            self.channel = configuration["discord"]["CHANNEL_ID"]
            self.redditon = configuration["reddit"]["enabled"]
            self.client_id = configuration["reddit"]["client_id"]
            self.client_secret = configuration["reddit"]["client_secret"]
            self.user_agent = configuration["reddit"]["user_agent"]
            self.username = configuration["reddit"]["username"]
            self.password = configuration["reddit"]["password"]
            self.sub_reddit = configuration["reddit"]["sub_reddit"]
            self.flair_id = configuration["reddit"]["flair_id"]

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

            # Ensure Featured has at least 1 item
            if (len(featured) <= 0):
                raise Exception(f"Featured: {len(featured)}")
        except Exception as e:
            log.critical(f"Failed to parse Item Shop items, {e}")

            return False

        raw_items = featured
        all_items = [item for item in raw_items if "sectionId" in item and item["sectionId"] is not None]
        def safe_key(x):
            try:
                return x["sectionId"]
            except (KeyError, TypeError):
                return 0
        all_items.sort(key=safe_key)
        num_items = len(all_items)
        columns_raw = math.ceil(math.sqrt(len(all_items)))
        if num_items <= 6:
            columns = columns_raw
        elif num_items <= 8:
            columns = columns_raw + 1
        else:
            columns = columns_raw + 2
        rows = math.ceil(num_items / columns)
        if num_items <= 8:
            width = 319 * math.ceil(num_items / 2)
        else:
            width = 319 * columns
        if rows <= 3:
            height = 600 * rows + 400
        elif rows <= 6:
            height = 585 * rows + 400
        else:
            height = 565 * rows + 400
        shopImage = Image.new("RGBA", (width, height))

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
        if columns <= 3:
            logo = ImageUtil.RatioResize(self, logo, 0, 140)
        elif columns <= 6:
            logo = ImageUtil.RatioResize(self, logo, 0, 190)
        else:
            logo = ImageUtil.RatioResize(self, logo, 0, 210)
        shopImage.paste(
            logo, ImageUtil.CenterX(self, logo.width, shopImage.width, 100), logo
        )

        if rows <= 6:
            datesize = 72
        else:
            datesize = rows * 7
        canvas = ImageDraw.Draw(shopImage)
        font = ImageUtil.Font(self, datesize)
        textWidth, _ = font.getsize(date)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, shopImage.width, 350),
            date,
            (255, 255, 255),
            font=font,
        )

        pool = Pool(16)
        generate_card = partial(Athena.GenerateCard,self)
        cards = pool.map(generate_card, all_items)
        cards = [c for c in cards if c is not None]

        for i,card in enumerate(cards):
            shopImage.paste(
                card,
                (
                    ((columns * 7) + ((i % columns) * (card.width + 5))),
                    475 + ((i // columns) * (card.height + 5)),
                ),
                card,
            )
        
        try:
            shopImage.save("itemshop.png")
            log.info("Generated Item Shop image")

            return True
        except Exception as e:
            log.critical(f"Failed to save Item Shop image, {e}\nImage Info:\nrows: {rows} x columns: {columns}\nwidth: {width} x height: {height}\ncount: {num_items}")

    def GenerateCard(self, item: dict):
        """Return the card image for the provided Fortnite Item Shop item."""

        def title_case(text):
            words = text.split()
            formatted_words = []
            for word in words:
                formatted_word = word[0].upper() + word[1:].lower()
                formatted_word = formatted_word.replace("'S", "'s")
                formatted_words.append(formatted_word)
            return ' '.join(formatted_words)

        try:
            if "bundle" in item and item["bundle"] is not None:
                name = title_case(item["bundle"]["name"])
                icon = item["bundle"]["image"]
                shop_time = "Bundle"
                category = "bundle"
            else:
                name = item["items"][0]["name"]
                if "images" in item and item["images"]["icon"] is None:
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
                category = item["items"][0]["type"]["value"]
            rarity = item["items"][0]["rarity"]["value"]
            if rarity == "gaminglegends":
                rarity = "gaming"
            price = item["finalPrice"]
        except Exception as e:
            log.error(f"Failed to parse item {name} ({rarity}/{category}/{price}), {e}")

            return

        colors = {
            "frozen": (148, 223, 255),
            "lava": (234, 141, 35),
            "legendary": (211, 120, 65),
            "dark": (251, 34, 223),
            "starwars": (231, 196, 19),
            "marvel": (197, 51, 52),
            "dc": (84, 117, 199),
            "icon": (54, 183, 183),
            "shadow": (113, 113, 113),
            "epic": (177, 91, 226),
            "rare": (73, 172, 242),
            "uncommon": (96, 170, 58),
            "common": (190, 190, 190),
            "gaming": (99, 99, 255),
            "slurp": (85, 150, 190),
        }

        blendColor = colors[rarity]
        if blendColor is None:
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
        elif (category == "bundle"):
            icon = ImageUtil.RatioResize(self, icon, 285, 350)
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
                    extraIcon = ImageUtil.Download(self, extraIcon)
                    extraIcon = ImageUtil.RatioResize(self, extraIcon, 75, 75)
                    if "bundle" in item and item["bundle"] is None:
                        try:
                            layer = ImageUtil.Open(self, f"box_bottom_{extraRarity}.png")
                        except FileNotFoundError:
                            log.warn(
                                f"Failed to open box_bottom_{extraRarity}.png, defaulted to Common"
                            )
                            layer = ImageUtil.Open(self, "box_bottom_common.png")

                        # we need to check that the extra-item icon isn't broken...
                        card.paste(
                            extraIcon,
                            (
                                (card.width - (layer.width + 9)),
                                (9 + ((i // 1) * (extraIcon.height))),
                            ),
                            extraIcon,
                        )

                        # then we can overwrite it
                        card.paste(
                            layer,
                            (
                                (card.width - (layer.width + 9)),
                                (9 + ((i // 1) * (layer.height))),
                            ),
                        )

                        # and put it back on top, if it isn't broken
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

                # this is where we are confirming the extra item is broken
                except Exception as e:
                    log.error(f"Failed to parse extra item for {name}, {e}")

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

        if "bundle" in item and item["bundle"] is not None:
            font = ImageUtil.Font(self, 36)
            textWidth, _ = font.getsize("Bundle")
            canvas.text(
                ImageUtil.CenterX(self, textWidth, card.width, 385),
                "Bundle",
                blendColor,
                font=font,
            )
        else:
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

        font = ImageUtil.Font(self, 30)
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
    except KeyboardInterrupt:
        log.info("Exiting...")
        exit()
