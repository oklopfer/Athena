# Athena v2

Athena v2 is a utility which generates the current Fortnite Item Shop into a stylized image.

## Requirements

- [Python](https://www.python.org/downloads/)
    - [requests](http://docs.python-requests.org/en/master/user/install/)
    - [coloredlogs](https://pypi.org/project/coloredlogs/)
    - [Pillow==9.5.0](https://pillow.readthedocs.io/en/stable/installation.html#basic-installation)
    - [discord.py](https://discordpy.readthedocs.io)
    - [praw](https://praw.readthedocs.io)

```bash
python3 -m pip install requests coloredlogs Pillow==9.5.0 discord.py praw
```

## Usage

Open `configuration_example.json` in your preferred text editor, fill the configurable values. Once finished, save and rename the file to `configuration.json`.

- `delayStart`: 
    - Input: set to number of seconds to delay fetch process
    - ValueType: `integer`

- `language`: 
    - Input: set the language for the Item Shop data ([Supported Languages](https://fortnite-api.com/documentation))
    - ValueType: `string`

- `discord`([discord.py](https://discordpy.readthedocs.io)):
    - `enabled`: 
        - Input: set to `true` or `false`
        - ValueType: `bool`

    - `TOKEN`: 
        - Input: set to your Discord Bot Token
        - ValueType: `string`

    - `CHANNEL_ID`: 
        - Input: set to ID of the channel for the bot to post in
        - ValueType: `integer`

- `reddit`([praw](https://praw.readthedocs.io)):
    - `enabled`: 
        - Input: set to `true` or `false`
        - ValueType: `bool`

    - `client_id`, `client_secret`, `user_agent`: 
        - Input: set to Reddit API credentials
        - ValueType: `string`

    - `username`, `password`: 
        - Input: set to Reddit User credentials
        - ValueType: `string`

    - `sub_reddit`: 
        - Input: set to the Subreddit you want the bot to post on
        - ValueType: `string`

    - `flair_id`: 
        - Input: set to the ID of the flair for the post
        - ValueType: `string`


Edit the images found in `assets/images/` to your liking, avoid changing image dimensions for optimal results.

Athena v2 is designed to be ran using a scheduler, such as [cron](https://en.wikipedia.org/wiki/Cron).

```bash
python3 itemshop.py
```

## Credits

- Item Shop data provided by [Fortnite-API](https://fortnite-api.com/)
- Burbank font property of [Adobe](https://fonts.adobe.com/fonts/burbank)
- Luckiest Guy font property of [Google](https://fonts.google.com/specimen/Luckiest+Guy)
