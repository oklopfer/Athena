import json
import logging
import math
import discord
import praw
from discord.ext import commands
from math import ceil
from sys import exit
from time import sleep
from datetime import datetime, timezone
from multiprocessing import Pool
from functools import partial

import coloredlogs
from PIL import Image, ImageDraw, ImageColor, ImageFilter, ImageChops

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
                {"responseFlags": 5},
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

    def create_border_layer(card_size, border_size=10, radius=0, fillcolor='yellow'):
        width, height = card_size
        border_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(border_layer)
        draw.rounded_rectangle([0, 0, width, height], radius, fill=fillcolor)
        inner_rect = [border_size, border_size, width - border_size, height - border_size]
        draw.rounded_rectangle(inner_rect, radius - border_size, fill=(0, 0, 0, 0))
        
        return border_layer

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
        for item in all_items:
            if "layout" in item:
                if "category" in item["layout"]:
                    if item["layout"]["category"] == "Spotlight":
                        item["gridCategory"] = "AAAAASpotlight"
                    elif item["layout"]["category"] == "Build with LEGO® Kits":
                        item["gridCategory"] = "ZZZZZBuild with LEGO® Kits"
                    else:
                        item["gridCategory"] = f"{item["layout"]["category"]}"
                else:
                    item["gridCategory"] = f"ZZZZZUnknown"
            else:
                item["gridCategory"] = f"ZZZZZUnknown"
        all_items.sort(key=lambda x: x["sortPriority"])
        all_items.sort(key=lambda x: x["layoutId"])
        all_items.sort(key=lambda x: x["layout"]["name"])
        all_items.sort(key=lambda x: (x["gridCategory"]))

        num_items = 0
        for item in all_items:
            item["gridSize"] = int(item['tileSize'].split('_')[1])
            num_items = num_items + item["gridSize"]
        rows_raw = math.ceil(num_items / 4)
        columns_raw = math.ceil(math.sqrt(rows_raw)) * 2
        if num_items <= 6:
            columns = columns_raw
        elif num_items <= 8:
            columns = columns_raw + 1
        else:
            columns = columns_raw + 5
        if (columns % 4) > 0:
            columns += 4 - (columns % 4)
        if columns < 4:
            columns = 4
        rows = math.ceil(num_items / columns) + 1
        block_width = 4
        gap_size = 250
        rowsabove = 1
        rowcount = 1
        metacolumn = 1
        position = 0
        metaposition = 0

        previous_layout = None
        block_x_offset = 0
        block_y_offset = 0
        current_position = 0
        block_y_offset_alt = 0
        rowsabove_alt = 0
        previous_offset = 0
        x_vals = []
        y_vals = []

        for i in all_items:
            current_layout = i["layout"]["name"]
            grid_size = i["gridSize"]
            metaposition += grid_size
            card_width = 340 * grid_size
            card_height = 545
            rowcount = ceil(metaposition / block_width)
            if current_layout != previous_layout:
                adjust = (metaposition - grid_size) % 4
                if adjust > 0:
                    metaposition += 4 - adjust
                rowcount = ceil(metaposition / block_width)
            if rowcount > rows:
                metacolumn += 1
                block_x_offset += (340 * 4) + gap_size
                metaposition = grid_size
                rowsabove_alt = 1
                block_y_offset_alt = card_height + gap_size
                rowcount = ceil(metaposition / block_width)
                current_position = 0
            if current_layout != previous_layout:
                current_position = 0
                rowsabove = 1
                block_y_offset += (card_height * rowsabove) + gap_size + previous_offset
                if block_y_offset_alt > 0:
                    block_y_offset = (card_height * rowsabove) + gap_size
                    block_y_offset_alt = 0
                position = grid_size
                previous_layout = current_layout
                layalt = 1
            else:
                position += grid_size
                rowsabove = ceil(position / block_width)
                if block_y_offset_alt > 0:
                    rowsabove = 1
                    block_y_offset = (card_height * rowsabove) + gap_size
                    block_y_offset_alt = 0
                    current_position = 0
            if ((grid_size == 4) and ((current_position + grid_size) % block_width) > 0) or ((grid_size >= 2) and ((current_position % 4) >= 3)):
                adjust = (4 - ((position + grid_size) % block_width))
                current_position += adjust
                position += adjust
                metaposition += adjust
                rowcount = ceil(metaposition / block_width)
            x_position = block_x_offset + (current_position % block_width) * (card_width // grid_size + 5) + 230
            y_position = block_y_offset + ((current_position // block_width) * (card_height + 5))
            previous_offset = y_position - block_y_offset
            x_vals.append(x_position + card_width)
            y_vals.append(y_position + card_height)
            current_position += grid_size

        width = max(x_vals) + 230
        height = max(y_vals) + 100
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
                (1, 4): (16, 26, 26, 380, 540, 150),
                (5, 8): (14, 24, 24, 160, 440, 200),
                (9, 12): (12, 21, 21, 70, 410, 200),
                (13, 16): (10, 17, 17, 70, 430, 200),
                (17, 23): (7, 13, 13, 70, 430, 200),
                (24, 27): (6, 11, 11, 80, 430, 200),
                (28, 31): (5, 9, 9, 90, 430, 200),
                (32, 35): (4, 8, 8, 120, 460, 200),
                (36, float('inf')): (4, 8, 8, 100, 460, 200)
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

        block_width = 4
        gap_size = 250
        rowsabove = 1
        rowcount = 1
        metacolumn = 1
        position = 0
        metaposition = 0

        previous_layout = None
        block_x_offset = 0
        block_y_offset = 0
        current_position = 0
        block_y_offset_alt = 0
        rowsabove_alt = 0
        previous_offset = 0

        for i, card in enumerate(cards):
            current_layout = all_items[i]["layout"]["name"]
            grid_size = all_items[i]["gridSize"]
            metaposition += grid_size
            rowcount = ceil(metaposition / block_width)
            if current_layout != previous_layout:
                adjust = (metaposition - grid_size) % 4
                if adjust > 0:
                    metaposition += 4 - adjust
                rowcount = ceil(metaposition / block_width)
            if rowcount > rows:
                metacolumn += 1
                block_x_offset += (340 * 4) + gap_size
                metaposition = grid_size
                rowsabove_alt = 1
                block_y_offset_alt = card.height + gap_size
                rowcount = ceil(metaposition / block_width)
                current_position = 0
            if current_layout != previous_layout:
                current_position = 0
                rowsabove = 1
                block_y_offset += (card.height * rowsabove) + gap_size + previous_offset
                if block_y_offset_alt > 0:
                    block_y_offset = (card.height * rowsabove) + gap_size
                    block_y_offset_alt = 0
                sub_font = ImageUtil.TitleFont(self, 80)
                textWidth, _ = sub_font.getsize(current_layout)
                textscale = 1
                if metacolumn > 1:
                    textscale = 2
                canvas.text(
                    ImageUtil.CenterX(self, textWidth, (textscale * block_x_offset) + textWidth + 450, block_y_offset - 130),
                    current_layout,
                    (255, 255, 255),
                    font=sub_font,
                )
                position = grid_size
                previous_layout = current_layout
            else:
                position += grid_size
                rowsabove = ceil(position / block_width)
                if block_y_offset_alt > 0:
                    rowsabove = 1
                    block_y_offset = (card.height * rowsabove) + gap_size
                    block_y_offset_alt = 0
                    current_position = 0

            if ((grid_size == 4) and ((current_position + grid_size) % block_width) > 0) or ((grid_size >= 2) and ((current_position % 4) >= 3)):
                adjust = (4 - ((position + grid_size) % block_width))
                current_position += adjust
                position += adjust
                metaposition += adjust
                rowcount = ceil(metaposition / block_width)

            x_position = block_x_offset + (current_position % block_width) * (card.width // grid_size + 5) + 230
            y_position = block_y_offset + ((current_position // block_width) * (card.height + 5))
            previous_offset = y_position - block_y_offset
            #print(f"{current_layout} / Row: {rowcount} / Position: {position} (Current: {current_position}; Meta: {metaposition}) / Column: {metacolumn} / Above: {rowsabove}")
            shopImage.paste(
                card,
                (
                    x_position,
                    y_position,
                ),
                card,
            )
            
            current_position += grid_size

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
                if "banner" in item and item["banner"]["value"] == "New!":
                    shop_time = "New!"
                    shop_time_flag = "new"
                    total_appearances = 1
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
                try:
                    icon = item["newDisplayAsset"]["renderImages"][0]["image"]
                except Exception as e:
                    try:
                        icon = item["newDisplayAsset"]["materialInstances"][0]["images"]["OfferImage"]
                    except Exception as e:
                        log.warn(f"No offerimage or renderimage for {name}.")
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
            leaves_date = datetime.fromisoformat(item["outDate"].replace('Z', '+00:00'))
            time_difference = leaves_date - datetime.now(timezone.utc)
            leaves_text = f"{time_difference.days}d {time_difference.seconds // 3600}h"

            if "brItems" in item:
                try:
                    rarity = item["brItems"][0]["rarity"]["value"]
                except Exception as e:
                    rarity = "common"
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

        if "colors" in item:
            if "color2" in item["colors"]:
                gradient = [
                    f"#{item['colors']['color1'][:6]}",
                    f"#{item['colors']['color3'][:6]}",
                    f"#{item['colors']['color2'][:6]}"
                ]
                textbgcolor = f"#{item["colors"]["color2"][:6]}"
            else:
                gradient = [
                    f"#{item['colors']['color1'][:6]}",
                    f"#{item['colors']['color3'][:6]}"
                ]
                textbgcolor = f"#{item["colors"]["color3"][:6]}"
        else:
            log.warn(f"No colors for {name}")
            textbgcolor = "#000000"
            gradient = ["#000000", "#000000", "#000000"]

        textcolor = "#FFFFFF"

        blendColor = textcolor

        gradient_rgb = [ImageColor.getrgb(color) for color in gradient]

        def interpolate_color(color1, color2, factor):
            return tuple(
                int(color1[i] + (color2[i] - color1[i]) * factor)
                for i in range(3)
            )

        def create_rounded_rectangle_mask(image_width, image_height, radius):
            mask = Image.new('L', (image_width, image_height), 0)
            draw = ImageDraw.Draw(mask)
            
            draw.rounded_rectangle([(0, 0), (image_width, image_height)], radius=radius, fill=255)
            
            return mask

        def reduce_brightness(color, factor):
            r, g, b = color
            r = int(r * factor)
            g = int(g * factor)
            b = int(b * factor)
            return (r, g, b)

        def create_gradient_layer(image_width, image_height, color, fade_percentage, max_opacity, corner_radius, brightness_factor=0.7):
            color = reduce_brightness(color, brightness_factor)
            
            gradient = Image.new('RGBA', (image_width, image_height), color + (0,))
            
            alpha_mask = Image.new('L', (image_width, image_height), 0)
            draw = ImageDraw.Draw(alpha_mask)
            
            fade_height = int(image_height * (1 - fade_percentage))
            
            for y in range(image_height):
                if y >= fade_height:
                    opacity = int(max_opacity * (y - fade_height) / (image_height - fade_height))
                    opacity = min(max_opacity, max(0, opacity))
                else:
                    opacity = 0
                
                draw.line([(0, y), (image_width, y)], fill=opacity)
            
            rounded_mask = create_rounded_rectangle_mask(image_width, image_height, corner_radius)
            alpha_mask = Image.composite(alpha_mask, Image.new('L', (image_width, image_height), 0), rounded_mask)
            
            gradient.putalpha(alpha_mask)

            return gradient

        card = Image.new("RGBA", (340 * item["gridSize"], 545))

        gradient_layer = Image.new("RGBA", card.size)
        draw = ImageDraw.Draw(gradient_layer)

        height = card.height

        for y in range(height):
            factor = y / height

            if len(gradient_rgb) == 2:
                color = interpolate_color(gradient_rgb[0], gradient_rgb[1], factor)
            else:
                if factor <= 0.5:
                    blend_factor = factor * 2
                    color = interpolate_color(gradient_rgb[0], gradient_rgb[1], blend_factor)
                else:
                    adjusted_factor = (factor - 0.5) / 0.7
                    blend_factor = min(adjusted_factor, 1)
                    color = interpolate_color(gradient_rgb[1], gradient_rgb[2], blend_factor)

            draw.line([(0, y), (card.width, y)], fill=color)


        radius = 40
        rounded_mask = create_rounded_rectangle_mask(card.width, card.height, radius)
        card.paste(gradient_layer, (0, 0), mask=rounded_mask)
        try:
            icon = ImageUtil.Download(self, icon)
        except Exception as e:
            if "brItems" in item:
                if "featured" in item["brItems"][0]["images"]:
                    icon = item["brItems"][0]["images"]["featured"]
                elif "icon" in item["brItems"][0]["images"]:
                    icon = item["brItems"][0]["images"]["icon"]
                else:
                    icon = item["brItems"][0]["images"]["smallIcon"]
            elif "legoKits" in item:
                icon = item["legoKits"][0]["images"]["small"]
            elif "instruments" in item:
                icon = item["instruments"][0]["images"]["large"]
            elif "cars" in item:
                icon = item["cars"][0]["images"]["large"]
            else:
                icon = "https://None"
            icon = ImageUtil.Download(self, icon)

        if item["gridSize"] == 1:
            if category == "outfit" or category == "bundle":
                if icon.width == 2048:
                    scale = 1.1
                elif category == "bundle":
                    if rarity == "racing":
                        scale = 1.4
                    else:
                        scale = 1.8
                else:
                    scale = 2.4
            else:
                scale = 1.3
        elif category == "outfit":
            scale = 1.3
        elif category == "bundle":
            if rarity == "racing":
                scale = 1.2
            else:
                scale = 1.1
        elif rarity == "festival":
            scale = 0.67
        elif category == "shoe":
            scale = 0.5
        else:
            scale = 1.2
        if (category == "outfit") or (category == "emote"):
            icon = ImageUtil.RatioResize(self, icon, 285 * item["gridSize"] * scale, 365)
        elif category == "wrap":
            icon = ImageUtil.RatioResize(self, icon, 230 * item["gridSize"] * scale, 310)
        elif (category == "bundle"):
            icon = ImageUtil.RatioResize(self, icon, 285 * item["gridSize"] * scale, 365)
        else:
            icon = ImageUtil.RatioResize(self, icon, 310 * item["gridSize"] * scale, 390)

        if icon.mode != "RGBA":
            icon = icon.convert("RGBA")

        if item["gridSize"] < 3:
            if item["gridSize"] == 1 and category == "outfit":
                scale = 40
            else:
                scale = 20
        elif category == "bundle" and rarity == "racing":
            scale = 50
        else:
            scale = 30
        card.paste(icon, ImageUtil.CenterX(self, icon.width, card.width, 35 - (scale * item["gridSize"])), icon)
        card.putalpha(rounded_mask)

        gradient_layer = create_gradient_layer(card.width, card.height, ImageColor.getrgb(textbgcolor), 0.5, 255, 40)
        card = Image.alpha_composite(card.convert('RGBA'), gradient_layer)

        canvas = ImageDraw.Draw(card)

        if shop_time == "New!":
            newborder = self.create_border_layer(card.size, border_size=13, radius=40, fillcolor='yellow')
            card.paste(newborder, (0, 0), newborder)
        elif "ago" in shop_time and days_difference >= 300:
            newborder = self.create_border_layer(card.size, border_size=13, radius=40, fillcolor='red')
            card.paste(newborder, (0, 0), newborder)           

        if "bundle" in item and item["bundle"] is not None:
            raritytext = "Bundle"
            font = ImageUtil.Font(self, 36)
            textWidth, _ = font.getsize(raritytext)
            canvas.text(
                ImageUtil.CenterX(self, textWidth, card.width, 375),
                raritytext,
                blendColor,
                font=font,
            )
        else:
            font = ImageUtil.Font(self, 36)
            if (category == "legoprop"):
                cattext = "Lego Prop"
            elif (category == "legoset"):
                cattext = "Lego Set"
            else:
                cattext = f"{category.capitalize()}"

            textWidth, _ = font.getsize(cattext)
            canvas.text(
                ImageUtil.CenterX(self, textWidth, card.width, 375),
                cattext,
                blendColor,
                font=font,
            )

        vbucks = ImageUtil.Open(self, "vbucks.png")
        vbucks = ImageUtil.RatioResize(self, vbucks, 25, 25)

        font = ImageUtil.Font(self, 30)
        if item["gridSize"] == 2:
            refactorsize = (200 + (item["gridSize"] * 70))
        elif item["gridSize"] > 2:
            refactorsize = (220 + (item["gridSize"] * 60))
        else:
            refactorsize = (240 + (item["gridSize"] * 30))
        if shop_time_flag != "bundle":
            if total_appearances != 1:
                textWidth, _ = font.getsize(f"{total_appearances} Visits")
                canvas.text(
                    ImageUtil.CenterX(self, ((textWidth / 2)), card.width - refactorsize, 378),
                    f"{total_appearances} Visits",
                    blendColor,
                    font=font,
                )
            else:
                if item["gridSize"] == 1:
                    offset = 381
                    font = ImageUtil.Font(self, 26)
                else:
                    offset = 378
                    font = ImageUtil.Font(self, 30)
                textWidth, _ = font.getsize(f"1 Visit!")
                canvas.text(
                    ImageUtil.CenterX(self, ((textWidth / 2)), card.width - refactorsize, offset),
                    f"First Visit!",
                    blendColor,
                    font=font,
                )
        else:
            if "banner" in item:
                if item["gridSize"] == 1:
                    offset = 381
                    font = ImageUtil.Font(self, 24)
                    bonkset = offset - 2
                else:
                    offset = 378
                    font = ImageUtil.Font(self, 30)
                    bonkset = offset
                bannertext = item["banner"]["value"]
                if "V-Bucks Off" in bannertext:
                    discount = item["regularPrice"] - item["finalPrice"]
                    discount = str(f"{(discount):,}")
                    bannertext = f"{discount} Off"
                    textWidth, _ = font.getsize(bannertext)
                    canvas.text(
                        ImageUtil.CenterX(self, ((textWidth / 2) - vbucks.width - 5), card.width - refactorsize, offset),
                        bannertext,
                        blendColor,
                        font=font,
                    )
                    card.paste(
                        vbucks,
                        ImageUtil.CenterX(self, (vbucks.width + (textWidth / 2) + 5), card.width - refactorsize, bonkset),
                        vbucks,
                    )
                else:
                    textWidth, _ = font.getsize(bannertext)
                    canvas.text(
                        ImageUtil.CenterX(self, ((textWidth / 2)), card.width - refactorsize, offset),
                        bannertext,
                        blendColor,
                        font=font,
                    )

        font = ImageUtil.Font(self, 30)
        textWidth, _ = font.getsize(f"{leaves_text}")
        canvas.text(
            ImageUtil.CenterX(self, ((textWidth / 2)), card.width + refactorsize - 80, 378),
            leaves_text,
            blendColor,
            font=font,
        )

        font = ImageUtil.Font(self, 36)
        price = str(f"{price:,}")
        textWidth, _ = font.getsize(price)
        canvas.text(
            ImageUtil.CenterX(self, ((textWidth - 5) - vbucks.width), (card.width - 175), 490),
            price,
            blendColor,
            font=font,
        )

        card.paste(
            vbucks,
            ImageUtil.CenterX(self, (vbucks.width + (textWidth + 5)), (card.width - 175), 493),
            vbucks,
        )

        textWidth, _ = font.getsize(shop_time)
        if shop_time_flag == "new":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth - 20)), (card.width + textWidth * 2.5), 490)
        elif shop_time_flag == "bundle":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth / 1.5)), (card.width + textWidth * 2), 490)
        elif shop_time_flag == "consecutive":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth - 10)), (card.width + textWidth / 1.5), 490)
        elif shop_time_flag == "since":
            shop_time_paste = ImageUtil.CenterX(self, ((textWidth - 5)), (card.width + textWidth - 25), 490)
        canvas.text(
            shop_time_paste,
            shop_time,
            blendColor,
            font=font,
        )

        font = ImageUtil.Font(self, 56)
        textWidth, _ = font.getsize(name)
        change = 0
        if textWidth >= 270:
            font, textWidth, change = ImageUtil.FitTextX(self, name, 56, 260 * item["gridSize"])
        canvas.text(
            ImageUtil.CenterX(self, textWidth, card.width, (423 + (change / 2))),
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
