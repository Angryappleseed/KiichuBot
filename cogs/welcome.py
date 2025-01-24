from discord.ext import commands
import discord
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        welcome_channel_id = 751367236966547457
        template_path = './images/Kiichan_Welcome.png'
        font_path = './fonts/Poppins-Regular.ttf'

        async with aiohttp.ClientSession() as session:
            async with session.get(str(member.avatar.replace(size=256).url)) as resp:
                avatar_bytes = await resp.read()

        with Image.open(template_path) as template:
            with Image.open(io.BytesIO(avatar_bytes)) as avatar:

                avatar = avatar.resize((350, 350))
                mask = Image.new('L', avatar.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0) + avatar.size, fill=255)

                avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
                avatar.putalpha(mask)



                border_size = 10
                total_size = (avatar.size[0] + border_size * 2, avatar.size[1] + border_size * 2)
                bordered_avatar = Image.new('RGBA', total_size, (255, 255, 255, 0))
                bordered_avatar.paste(avatar, (border_size, border_size), avatar)





                template_width, template_height = template.size
                avatar_width, avatar_height = bordered_avatar.size
                avatar_position = ((template_width - avatar_width) // 2, (template_height - avatar_height) // 2 - 57)

                template.paste(bordered_avatar, avatar_position, bordered_avatar)

                draw = ImageDraw.Draw(template)

               
                try:
                    font = ImageFont.truetype(font_path, 48)
                except IOError:
                    font = ImageFont.load_default()

                username = member.name[:20] + '...' if len(member.name) > 20 else member.name

                left, top, right, bottom = font.getbbox(username)
                text_width = right - left
                text_height = bottom - top
                text_position = ((template_width - text_width) // 2, avatar_position[1] + avatar_height + 10)

                draw.text(text_position, username, fill=(0, 0, 0), font=font)




                output_buffer = io.BytesIO()
                template.save(output_buffer, 'PNG')
                output_buffer.seek(0)

                # Send the welcome message with the image
                file = discord.File(fp=output_buffer, filename="welcome_image.png")
                channel = self.bot.get_channel(welcome_channel_id)

                if channel:
                    await channel.send(f"Welcome to the server, {member.mention}!", file=file)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
