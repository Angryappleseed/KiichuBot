
#----------YOUTUBE AND TWITCH FEED TRACKERS------------------#

import json
from datetime import datetime
import os
import discord
from discord.ext import tasks, commands
import googleapiclient.discovery

from helpers.database import(
    update_last_video_id, 
    get_last_video_id
    )


class Feeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.youtube_channel_id = 'UC9XP29KKVyQ_lhQQL_4Cg2g'
        self.last_video_id = None


    @commands.Cog.listener()
    async def on_ready(self):
        # Retrieve the last video ID from the database when the bot is ready
        self.last_video_id, self.last_publish_date = await get_last_video_id(self.youtube_channel_id)
        self.check_new_video.start()
        print("loop started")

    @tasks.loop(minutes=1)
    async def check_new_video(self):
        print("Checking for new videos...")
        await self.bot.wait_until_ready()
        try:
            new_videos = await self.get_latest_video()
            for video in new_videos:
                print("New video found, sharing...")
                await self.share_new_video(video)
            if not new_videos:
                print("No new video found.")
        except Exception as e:
            print(f"Error during video check: {e}")



#----------Get Latest Video----------------------#

    async def get_latest_video(self):
        new_videos = []
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
                maxResults=5 
            )
            response = request.execute()
            
            if response['items']:
                _, last_publish_date_str = await get_last_video_id(self.youtube_channel_id)
                last_publish_date = datetime.fromisoformat(last_publish_date_str.replace("Z", "+00:00")) if last_publish_date_str else None
                
                for video in response['items']:
                    video_id = video['id']['videoId']
                    publish_date_str = video['snippet']['publishedAt']
                    publish_date = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00"))
                    
                    if last_publish_date is None or publish_date > last_publish_date:
                        new_videos.append(video)
                
                if new_videos:
                    newest_video = new_videos[0]
                    newest_video_id = newest_video['id']['videoId']
                    newest_publish_date_str = newest_video['snippet']['publishedAt']
                    await update_last_video_id(self.youtube_channel_id, newest_video_id, newest_publish_date_str)
                    
        except Exception as e:
            print(f"Error fetching the latest video: {e}")
        
        return new_videos




    async def share_new_video(self, video):
        video_id = video['id']['videoId']
        video_title = video['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            channel = self.bot.get_channel(int("1213369972143824906"))  # Ensure channel ID is an integer
            if channel:
                await channel.send(f"New video uploaded: **{video_title}**\n{video_url}")
                print("Shared new video to channel.")
            else:
                print("Channel not found.")
        except Exception as e:
            print(f"Error sharing the new video: {e}")

async def setup(bot):
    await bot.add_cog(Feeds(bot))