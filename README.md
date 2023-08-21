# Athena v2

Athena v2 is a utility which generates the current Fortnite Item Shop into a stylized image.

## Requirements

- [Python](https://www.python.org/downloads/)
    - [requests](http://docs.python-requests.org/en/master/user/install/)
    - [coloredlogs](https://pypi.org/project/coloredlogs/)
    - [Pillow==9.5.0](https://pillow.readthedocs.io/en/stable/installation.html#basic-installation)

```bash
python3 -m pip install requests coloredlogs Pillow==9.5.0 discord.py
```

## Usage

Open `configuration_example.json` in your preferred text editor, fill the configurable values. Once finished, save and rename the file to `configuration.json`.

- `delayStart`: Set to `0` to begin the process immediately
- `language`: Set the language for the Item Shop data ([Supported Languages](https://fortnite-api.com/documentation))

Edit the images found in `assets/images/` to your liking, avoid changing image dimensions for optimal results.

Athena v2 is designed to be ran using a scheduler, such as [cron](https://en.wikipedia.org/wiki/Cron).

```bash
python3 itemshop.py
```

## Credits

- Item Shop data provided by [Fortnite-API](https://fortnite-api.com/)
- Burbank font property of [Adobe](https://fonts.adobe.com/fonts/burbank)
- Luckiest Guy font property of [Google](https://fonts.google.com/specimen/Luckiest+Guy)
