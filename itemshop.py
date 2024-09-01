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
                "https://fortnite-api.com/v2/shop",
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
            raw_items = itemShop["entries"]
                
            if not raw_items:
                log.warning("No items in the item shop")
                return False

        except Exception as e:
            log.critical(f"Failed to parse Item Shop items, {e}, {raw_items}")
            return False

        all_items = [
            item for item in raw_items 
            if "layoutId" in item and item["layoutId"] is not None and not item["layoutId"].startswith("JamTracks") and not "tracks" in item
        ]

        all_items.sort(key=lambda x: x["layoutId"])
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
            height = 580 * rows + 400
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

        def calculate_sizes(columns):
            ranges = {
                (1, 3): (15, 28, 28, 275, 400, 100),
                (4, 5): (14, 26, 26, 200, 350, 100),
                (6, 7): (12, 24, 24, 150, 350, 200),
                (8, 10): (9, 21, 21, 125, 350, 200),
                (11, 12): (9, 18, 18, 125, 350, 200),
                (13, 16): (7, 15, 15, 125, 350, 200),
                (17, 18): (6, 13, 13, 125, 350, 200),
                (19, 21): (4, 11, 11, 125, 350, 200),
                (22, float('inf')): (3, 10, 10, 125, 350, 200)
            }

            for (start, end), values in ranges.items():
                if start <= columns <= end:
                    return values

        datesize, codesize, subfontsize, title_top, date_top, push = calculate_sizes(columns)
        datesize = datesize * columns
        codesize = codesize * columns
        subfontsize = subfontsize * columns

        canvas = ImageDraw.Draw(shopImage)
        font = ImageUtil.Font(self, datesize)
        textWidth, _ = font.getsize(date)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, (textWidth + push), date_top),
            date,
            (255, 255, 255),
            font=font,
        )
        below_code="Use our code! #EpicPartner"
        textWidth, _ = font.getsize(below_code)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, (shopImage.width * 2 - (textWidth + push)), date_top),
            "Use our code! #EpicPartner",
            (255, 255, 255),
            font=font,
        )
        creator_code="FNFASHION"
        code_font = ImageUtil.TitleFont(self, codesize)
        textWidth, _ = code_font.getsize(creator_code)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, (shopImage.width * 2 - (textWidth + push)), title_top),
            creator_code,
            (255, 255, 255),
            font=code_font,
        )
        subreddit_name="r/FortniteFashion"
        sub_font = ImageUtil.TitleFont(self, subfontsize)
        textWidth, _ = code_font.getsize(subreddit_name)
        canvas.text(
            ImageUtil.CenterX(self, textWidth, (textWidth + push), title_top),
            subreddit_name,
            (255, 255, 255),
            font=sub_font,
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
                shop_time_flag = "bundle"
            else:
                if "brItems" in item:
                    name = item["brItems"][0]["name"]
                    category = item["brItems"][0]["type"]["value"]
                elif "legoKits" in item:
                    name = item["legoKits"][0]["name"]
                    category = item["legoKits"][0]["type"]["value"]
                elif "instruments" in item:
                    name = item["instruments"][0]["name"]
                    category = item["instruments"][0]["type"]["value"]
                elif "cars" in item:
                    name = item["cars"][0]["name"]
                    category = item["cars"][0]["type"]["value"]
                else:
                    name = "Unknown"
                    category = "Unknown"
                if "brItems" in item:
                    if item["brItems"][0]["images"]["icon"] is None:
                        if "featured" in item["brItems"][0]["images"]:
                            icon = item["brItems"][0]["images"]["featured"]
                        else:
                            icon = item["brItems"][0]["images"]["smallIcon"]
                    else:
                        icon = item["brItems"][0]["images"]["icon"]
                elif "tracks" in item:
                    icon = item["tracks"][0]["albumArt"]
                elif "legoKits" in item:
                    icon = item["legoKits"][0]["images"]["small"]
                elif "instruments" in item:
                    icon = item["instruments"][0]["images"]["large"]
                elif "cars" in item:
                    icon = item["cars"][0]["images"]["large"]
                else:
                    icon = "https://None"
                shopHistory = None
                if "tracks" in item and item["tracks"] is not None:
                    shopHistory = item["tracks"][0]["shopHistory"]
                elif "brItems" in item and item["brItems"] is not None:
                    shopHistory = item["brItems"][0]["shopHistory"]
                elif "legoKits" in item and item["legoKits"] is not None:
                    shopHistory = item["legoKits"][0]["shopHistory"]
                elif "instruments" in item and item["instruments"] is not None:
                    shopHistory = item["instruments"][0]["shopHistory"]
                elif "cars" in item and item["cars"] is not None:
                    shopHistory = item["cars"][0]["shopHistory"]
                if shopHistory is not None:
                    shopHistory_dates = [datetime.fromisoformat(date_string) for date_string in shopHistory]
                    total_appearances = len(shopHistory_dates)
                    if total_appearances < 2:
                        shop_time = "New!"
                        shop_time_flag = "new"
                    else:
                        days_difference = (shopHistory_dates[-1] - shopHistory_dates[-2]).days
                        if days_difference == 1:
                            current_date = shopHistory_dates[-1]
                            days_consecutive = 1
                            for i in range(total_appearances - 2, -1, -1):
                                if (current_date - shopHistory_dates[i]).days == 1:
                                    days_consecutive += 1
                                    current_date = shopHistory_dates[i]
                                else:
                                    break
                            if days_consecutive > 1:
                                shop_time = f"In for {days_consecutive} days"
                                shop_time_flag = "consecutive"
                            else:
                                shop_time = "1 day ago"
                                shop_time_flag = "since"
                        else:
                            shop_time = f"{days_difference} days ago"
                            shop_time_flag = "since"
            if "brItems" in item:
                rarity = item["brItems"][0]["rarity"]["value"]
                if rarity == "gaminglegends":
                    rarity = "gaming"
            elif "legoKits" in item:
                rarity = "lego"
            elif "instruments" in item:
                rarity = "festival"
            elif "cars" in item:
                rarity = "racing"
            else:
                rarity = "common"
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
            "marvel": (196, 54, 55),
            "dc": (84, 117, 199),
            "icon": (54, 183, 183),
            "shadow": (113, 113, 113),
            "epic": (177, 91, 226),
            "rare": (73, 172, 242),
            "uncommon": (96, 170, 58),
            "common": (190, 190, 190),
            "gaming": (99, 99, 255),
            "slurp": (85, 150, 190),
            "lego": (255, 215, 0),
            "racing": (19, 111, 232),
            "festival": (145, 131, 245),
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

        try:
            offerimage = item["newDisplayAsset"]["materialInstances"][0]["images"]["OfferImage"]
        except Exception as e:
            log.warn(f"No offerimage for {name}")
            offerimage = "https://None"
        try:
            icon = ImageUtil.Download(self, icon)
        except Exception as e:
            log.warn((f"Icon for {name} not found, switching to small"))
            icon = "https://None"
            icon = ImageUtil.Download(self, icon)
        if (category == "outfit") or (category == "emote"):
            icon = ImageUtil.RatioResize(self, icon, 285, 365)
        elif category == "wrap":
            icon = ImageUtil.RatioResize(self, icon, 230, 310)
        elif (category == "bundle"):
            icon = ImageUtil.RatioResize(self, icon, 285, 350)
        else:
            icon = ImageUtil.RatioResize(self, icon, 310, 390)
        if icon.mode == "RGBA":
            alpha = icon.split()[3]
            card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), mask=alpha)
        else:
            alpha = None
            try:
                card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), icon)
            except Exception as e:
                log.warn(f"{e} for {name} ({rarity}/{category}/{price}), trying smallIcon.")
                if "brItems" in item:
                    icon = item["brItems"][0]["images"]["smallIcon"]
                elif "instruments" in item:
                    icon = item["instruments"][0]["images"]["small"]
                elif "cars" in item:
                    icon = item["cars"][0]["images"]["small"]
                try:
                    icon = ImageUtil.Download(self, icon)
                    icon = ImageUtil.RatioResize(self, icon, 285, 365)
                    card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), icon)
                except Exception as e:
                    if (offerimage != "https://None"):
                        log.warn(f"{e} for {name} ({rarity}/{category}/{price}), trying offerimage.")
                        try:
                            offericon = ImageUtil.Download(self, offerimage)
                            offericon = ImageUtil.RatioResize(self, offericon, 285, 365)
                            card.paste(offericon, ImageUtil.CenterX(self, icon.width, card.width, 15), offericon)
                        except Exception as e:
                            log.warn(f"{e} for {name} ({rarity}/{category}/{price}), trying offerimage with no transparency.")
                            try:
                                card.paste(offericon, ImageUtil.CenterX(self, icon.width, card.width, 15), mask=alpha)
                            except Exception as e:
                                log.warn(f"{e} for {name} ({rarity}/{category}/{price}), falling back to smallIcon and no transparency.")
                                card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), mask=alpha)
                    else:
                        log.warn(f"{e} for {name} ({rarity}/{category}/{price}), falling back to smallIcon and no transparency.")
                        card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 15), mask=alpha)


        if "brItems" in item:
            lent = item["brItems"]
        elif "instruments" in item:
            lent = item["instruments"]
        elif "legoKits" in item:
            lent = item["legoKits"]
        elif "cars" in item:
            lent = item["cars"]
        if len(lent) > 1:
            # Track grid position
            i = 0

            # Start at position 1 in items array
            for extra in lent[1:]:
                if not "bundle" in item:
                    try:
                        extraRarity = extra["rarity"]["value"]
                        if  extraRarity == "gaminglegends":
                            extraRarity = "gaming"
                        extraIcon = extra["images"]["smallIcon"]
                        try:
                            extraIcon = ImageUtil.Download(self, extraIcon)
                        except Exception as e:
                            log.warn(f"Extra smallIcon for {name} not found, switching to featured")
                            extraIcon = extra["images"]["featured"]
                            extraIcon = ImageUtil.Download(self, extraIcon)
                        extraIcon = ImageUtil.RatioResize(self, extraIcon, 75, 75)
                        try:
                            layer = ImageUtil.Open(self, f"box_bottom_{extraRarity}.png")
                        except FileNotFoundError:
                            log.warn(
                                f"Failed to open box_bottom_{extraRarity}.png, defaulted to Common"
                            )
                            layer = ImageUtil.Open(self, "box_bottom_common.png")

                        # Calculate position
                        position = (
                            card.width - (layer.width + 9),
                            9 + ((i // 1) * extraIcon.height),
                        )

                        card.paste(extraIcon, position, extraIcon)
                        card.paste(layer, position)
                        card.paste(extraIcon, position, extraIcon)

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
            font = ImageUtil.Font(self, 30)
            if "legoKits" in item or "cars" in item or "instruments" in item:
                raritytext = f"{rarity.capitalize()} Bundle"
            else:
                raritytext = "Bundle"
                font = ImageUtil.Font(self, 36)
            textWidth, _ = font.getsize(raritytext)
            canvas.text(
                ImageUtil.CenterX(self, textWidth, card.width, 385),
                raritytext,
                blendColor,
                font=font,
            )
        else:
            font = ImageUtil.Font(self, 30)
            if (category == "legoprop"):
                cattext = "Prop"
            else:
                cattext = f"{category.capitalize()}"
            raritytext = f"{rarity.capitalize()} {cattext}"

            textWidth, _ = font.getsize(raritytext)
            canvas.text(
                ImageUtil.CenterX(self, textWidth, card.width, 385),
                raritytext,
                blendColor,
                font=font,
            )

        vbucks = ImageUtil.Open(self, "vbucks.png")
        vbucks = ImageUtil.RatioResize(self, vbucks, 25, 25)

        font = ImageUtil.Font(self, 16)
        if shop_time_flag != "bundle":
            if total_appearances == 1:
                textWidth, _ = font.getsize("First")
                canvas.text(
                    ImageUtil.CenterX(self, ((textWidth / 2)), (card.width - 252), 350),
                    "First",
                    blendColor,
                    font=font,
                )
                textWidth, _ = font.getsize("Shop Visit!")
                canvas.text(
                    ImageUtil.CenterX(self, ((textWidth / 2)), (card.width - 235), 366),
                    "Shop Visit!",
                    blendColor,
                    font=font,
                )
            else:
                total_appearances = str(total_appearances)
                textWidth, _ = font.getsize(total_appearances)
                canvas.text(
                    ImageUtil.CenterX(self, ((textWidth / 2)), (card.width - 255), 350),
                    total_appearances,
                    blendColor,
                    font=font,
                )
                textWidth, _ = font.getsize("Shop Visits")
                canvas.text(
                    ImageUtil.CenterX(self, ((textWidth / 2)), (card.width - 235), 366),
                    "Shop Visits",
                    blendColor,
                    font=font,
                )

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
        if shop_time_flag == "new":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth - 20)), (card.width + textWidth * 2.5), 495)
        elif shop_time_flag == "bundle":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth / 1.5)), (card.width + textWidth * 2), 495)
        elif shop_time_flag == "consecutive":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth - 10)), (card.width + textWidth / 1.5), 495)
        elif shop_time_flag == "since":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth - 5)), (card.width + textWidth - 25), 495)
        canvas.text(
            shop_time_paste,
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
