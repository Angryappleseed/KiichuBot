import json
import os
import discord
from discord.ext import tasks, commands
import googleapiclient.discovery

from helpers.database import(
    update_recent_video_ids, 
    get_recent_video_ids
    )


class Feeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube_channel_id = 'UC_oDyNQnhSFpKlyQl4q0b9w'  # Your YouTube channel ID
        # Initialize as an empty list
        self.recent_video_ids = []

    @commands.Cog.listener()
    async def on_ready(self):
        # Fetch the recent video IDs from the database
        self.recent_video_ids = await get_recent_video_ids(self.youtube_channel_id)
        self.check_new_video.start()
        print("Checking for new videos loop started")

    @tasks.loop(seconds=20)
    async def check_new_video(self):
        print("Checking for new videos...")
        new_videos = await self.get_latest_videos(5)  # Adjust to fetch 5 latest videos
        if new_videos:
            for video in new_videos:
                await self.share_new_video(video)

    async def get_latest_videos(self, number_of_videos=5):
        try:
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
            api_key = config["YOUTUBE_API_KEY"]
            youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
            
            request = youtube.search().list(
                part="snippet",
                channelId=self.youtube_channel_id,
                order="date",
                type="video",
                maxResults=number_of_videos
            )
            response = request.execute()
            
            new_videos = []
            for item in response['items']:
                video_id = item['id']['videoId']
                if video_id not in self.recent_video_ids:
                    new_videos.append(item)
            
            # Update the list of recent video IDs if we found new videos
            if new_videos:
                self.recent_video_ids = [video['id']['videoId'] for video in response['items']]
                # Update the database with the new list
                await update_recent_video_ids(self.youtube_channel_id, self.recent_video_ids)
            
            return new_videos
        except Exception as e:
            print(f"Error fetching the latest videos: {e}")
        return []

    async def share_new_video(self, video):
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        channel_id = int("1213369972143824906")  # Replace with your target channel ID
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(f"New video uploaded: **{video_title}**\n{video_url}")
            print(f"Shared new video to channel: {video_title}")
        else:
            print("Channel not found.")

async def setup(bot):
    await bot.add_cog(Feeds(bot))