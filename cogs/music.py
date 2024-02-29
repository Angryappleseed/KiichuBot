
#---------------------MUSIC COMMANDS---------------------#

import asyncio
import functools
import itertools
import math
import random
import time

import discord
import yt_dlp as youtube_dl
from async_timeout import timeout
from discord.ext import commands
from discord import app_commands


from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes

youtube_dl.utils.bug_reports_message = lambda: ''




ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.75"'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)




class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1):
        super().__init__(source, volume)

        self.requester = data.get('requester', None)
        self.title = data.get('title')
        self.url = data.get('url')
        self.webpage_url = data.get('webpage_url')
        self.thumbnail = data.get('thumbnail', None)
        self.duration = self.parse_duration(data.get('duration'))

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        cls.webpage_url = data.get('webpage_url')

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)



    @staticmethod
    def parse_duration(duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes}:{seconds:02}"




class VoiceState:
    def __init__(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.voice = None
        self.next = asyncio.Event()
        self.music_queue = MusicQueue()
        self.exists = True
        self.command_channel = ctx.channel
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        return self.voice and self.voice.is_playing()

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.voice or not self.voice.is_playing():
                # Fetch the next song from the queue
                next_song = self.music_queue.next_song()
                if next_song:
                    self.current = next_song
                    await self.command_channel.send(embed=self.current.create_embed())
                    self.voice.play(self.current.source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
                else:
                    break  # No more songs to play

            await self.next.wait()

            if self.music_queue.loop_queue and not self.music_queue.loop_song:
                # Add the song back to the queue if loop_queue is True
                self.music_queue.add_song(self.current)

            if not self.exists:
                return

    async def stop(self):
        self.exists = False
        self.voice.stop()
        await self.voice.disconnect()



    def toggle_loop(self):
        if not self.music_queue.loop_song and not self.music_queue.loop_queue:
            self.music_queue.loop_song = True
        elif self.music_queue.loop_song:
            self.music_queue.loop_song = False
            self.music_queue.loop_queue = True
        else:
            self.music_queue.loop_song = False
            self.music_queue.loop_queue = False
        return self.music_queue.loop_song, self.music_queue.loop_queue





class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current_index = -1
        self.loop_song = False
        self.loop_queue = False

    def add_song(self, song):
        self.queue.append(song)

    def next_song(self):
        if self.loop_song:
            return self.current_song()
        self.current_index = (self.current_index + 1) % len(self.queue)
        return self.queue[self.current_index]

    def prev_song(self):
        if self.current_index > 0:
            self.current_index -= 1
        return self.queue[self.current_index]

    def current_song(self):
        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def toggle_loop_song(self):
        self.loop_song = not self.loop_song
        self.loop_queue = False  # Reset queue loop when song loop is toggled

    def toggle_loop_queue(self):
        self.loop_queue = not self.loop_queue
        self.loop_song = False  # Reset song loop when queue loop is toggled

    



class Song:
    def __init__(self, source):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now Playing',
                               description=f'**[{self.source.title}]({self.source.webpage_url})**',
                               color=colors['blue'])
                 .add_field(name=f'Duration:', value=self.source.duration)
                 .add_field(name='Requested by:', value=self.requester.mention)
                 .set_thumbnail(url=self.source.thumbnail))
        return embed
    




class Music(commands.Cog, name="music"):
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx):
        state = self.voice_states.get(ctx.guild.id)
        if not state or not state.exists:
            state = VoiceState(ctx)
            self.voice_states[ctx.guild.id] = state
        return state
        

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot and member.id == self.bot.user.id:
            if before.channel and not after.channel:
                guild_id = before.channel.guild.id
                print(f"Bot disconnected from voice channel in guild {guild_id}")
                if guild_id in self.voice_states:
                    voice_state = self.voice_states[guild_id]
                    await voice_state.stop()

                    if voice_state.command_channel:
                        print(f"Command channel ID: {voice_state.command_channel.id}")
                        try:
                            embed = discord.Embed(
                                title="Disconnected",
                                description=f"I've been kicked from the voice channel. {emotes['cry']}",
                                color=colors['red']
                            )
                            await voice_state.command_channel.send(embed=embed)
                            print("Embed sent successfully")
                        except Exception as e:
                            print(f"Failed to send disconnection message: {e}, in guild {guild_id}, channel {voice_state.command_channel.id}")
                    else:
                        print("Command channel not set")

                    del self.voice_states[guild_id]



#-------------------JOIN---------------------------#
    @commands.hybrid_command(name="join", description="Algebra will vibe with you in vc.")
    async def _join(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        if not channel:
            if not ctx.author.voice:
                embed = discord.Embed(description=f'You are not connected to a voice channel. {emotes["ded"]}',
                                color=colors['red'])
                return await ctx.send(embed=embed)


            channel = ctx.author.voice.channel

        voice_state = self.get_voice_state(ctx)
        voice_state.command_channel = ctx.channel

        if voice_state.voice:
            await voice_state.voice.move_to(channel)
            return await ctx.send(f"Moved to {channel.name}")

        voice_state.voice = await channel.connect()
        await ctx.send(f"Connected to {channel.name}")



#------------------------PLAY----------------------------#
    @commands.hybrid_command(name="play", description="Play a song.")
    async def _play(self, ctx: commands.Context, *, search: str):
        if not ctx.author.voice:
            return await ctx.reply(f"You are not connected to a voice channel. {emotes['think']}")

        voice_state = self.get_voice_state(ctx)

        if not voice_state.voice or not voice_state.voice.is_connected():
            voice_state.voice = await ctx.author.voice.channel.connect()

        source = await YTDLSource.from_url(search, loop=self.bot.loop, stream=True)
        song = Song(source)
        voice_state.music_queue.add_song(song)
        await ctx.reply(f"Added {source.title} to the queue.")



    #-----------------------------LOOP------------------------------------#
    @commands.hybrid_command(name="loop", description="Loop the current song or queue.")
    async def _loop(self, ctx: commands.Context):
        voice_state = self.get_voice_state(ctx)
        song_loop, queue_loop = voice_state.toggle_loop()
        if song_loop:
            await ctx.reply("Looping current song.")
        elif queue_loop:
            await ctx.reply("Looping the queue.")
        else:
            await ctx.reply("Looping disabled.")





    @commands.hybrid_command(name="skip", description="Skip the current song.")
    async def _skip(self, ctx: commands.Context):
        voice_state = self.get_voice_state(ctx)
        if voice_state.music_queue.next_song():
            voice_state.next.set()
            await ctx.reply("Skipped to the next song.")
        else:
            await ctx.reply("No more songs in the queue.")



    @commands.hybrid_command(name="queue", description="Display the song queue.")
    async def _queue(self, ctx: commands.Context):
        voice_state = self.get_voice_state(ctx)
        queue = voice_state.music_queue.queue
        if queue:
            queue_list = "\n".join([f"{idx + 1}. {song.title}" for idx, song in enumerate(queue)])
            await ctx.reply(f"Current Queue:\n{queue_list}")
        else:
            await ctx.reply("The queue is currently empty.")



    @commands.hybrid_command(name="nowplaying", description="Show the currently playing song.")
    async def _nowplaying(self, ctx: commands.Context):
        voice_state = self.get_voice_state(ctx)
        current_song = voice_state.music_queue.current_song()
        if current_song:
            await ctx.reply(f"Now playing: {current_song.source.title}")
        else:
            await ctx.reply("No song is currently playing.")


    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f'An error occurred: {str(error)}')

    def cog_unload(self):
        for state in self.voice_states.values():
            state.exists = False
            self.bot.loop.create_task(state.stop())

async def setup(bot):
    await bot.add_cog(Music(bot))