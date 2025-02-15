import os
from datetime import datetime
from pathlib import Path

import click
import pytz
import twitter
from slugify import slugify

from . import utils


@click.group()
def cli():
    """Send a tweet."""
    pass


@cli.command()
@click.argument("handle")
@click.option("-i", "--input-dir", "input_dir", default="./")
def single(handle, input_dir):
    """Tweet a single source."""
    # Pull the source’s metadata
    data = utils.get_site(handle)

    # Connect to Twitter
    api = twitter.Api(
        consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
        consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
        access_token_key=os.getenv("TWITTER_ACCESS_TOKEN_KEY"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )

    # Get the timestamp
    now = datetime.now()

    # Convert it to local time
    tz = pytz.timezone(data["timezone"])
    now_local = now.astimezone(tz)

    # Create the headline
    tweet = f"The @{handle} homepage at {now_local.strftime('%-I:%M %p')} local time"

    # Get the image
    input_path = Path(input_dir)
    input_path.mkdir(parents=True, exist_ok=True)
    image_path = input_path / f"{handle}.jpg"
    io = open(image_path, "rb")
    media_id = api.UploadMediaSimple(io)

    # Post the media
    api.PostMediaMetadata(media_id, tweet)

    # Make the tweet
    api.PostUpdate(tweet, media=media_id)


@cli.command()
@click.argument("slug")
@click.option("-i", "--input-dir", "input_dir", default="./")
def bundle(slug, input_dir):
    """Tweet four sources as a single tweet."""
    # Pull the source metadata
    bundle = utils.get_bundle(slug)
    target_list = [h for h in utils.get_site_list() if h["bundle"] == slug]

    # Connect to Twitter
    api = twitter.Api(
        consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
        consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
        access_token_key=os.getenv("TWITTER_ACCESS_TOKEN_KEY"),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
    )

    # Get the timestamp
    now = datetime.now()

    # Convert it to local time
    tz = pytz.timezone(bundle["timezone"])
    now_local = now.astimezone(tz)

    # Set hashtags
    slug = slugify(bundle["name"], separator="")
    date_str = now_local.strftime("%Y%m%d")
    hashtags = f"#{slug} #date{date_str}"

    # Loop through all the targets
    media_list = []
    for i, target in enumerate(target_list):
        # Get the list item
        emoji = utils.numoji(i + 1)
        list_item = f"\n{emoji} @{target['handle']}"

        # Get the image
        input_path = Path(input_dir)
        input_path.mkdir(parents=True, exist_ok=True)
        image_path = input_path / f"{target['handle']}.jpg"
        io = open(image_path, "rb")
        media_id = api.UploadMediaSimple(io)

        # Get the timestamp
        target_now = datetime.now()

        # Convert it to local time
        tz = pytz.timezone(target["timezone"])
        target_local = target_now.astimezone(tz)

        # Add the alt text to the image
        alt_text = f"The @{target['handle']} homepage at {target_local.strftime('%-I:%M %p')} local time"
        api.PostMediaMetadata(media_id, alt_text)

        # Add it to our list
        media_list.append([list_item, media_id])

    chunk_list = utils.chunk(media_list, 4)
    parent_status_id = None
    for i, chunk in enumerate(chunk_list):
        # Set the headline, if it's the first tweet in the thread
        if i == 0:
            tweet = f"{bundle['name']} homepages at {now_local.strftime('%-I:%M %p')} in {bundle['location']}\n"
        else:
            tweet = ""

        # Build the lists
        media_list = []
        for list_item, media_id in chunk:
            tweet += list_item
            media_list.append(media_id)
        tweet += f"\n\n{hashtags}"

        # Make the tweet
        if i == 0:
            status = api.PostUpdate(tweet, media=media_list)
        else:
            status = api.PostUpdate(
                tweet, media=media_list, in_reply_to_status_id=parent_status_id
            )
        parent_status_id = status.id


if __name__ == "__main__":
    cli()
