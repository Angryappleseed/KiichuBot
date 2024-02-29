# AlgebraBot
## Current Version: 1.0.0
## Developed by: Angryappleseed
This is a multi-purpose discord.py bot which I am working on as a passion-project.

Since this is a WIP and just a passion project, many features are incomplete/many bugs may arise and I may be slow to/never fix them.

Also, you can assume that many parts will be undocumented or difficult to interpret. The source code here is just meant to be a reference.

<p align="center">
  <img src='./images/algebrabanner.png' width=100%>
</p>


## Setup:
Preferably, I would not want you to run your own instance of this bot. 

Just invite my AlgebraBot to your server, if you plan on using it, to support me. You can invite it with this [link](https://discordapp.com/oauth2/authorize?&client_id=1073891402108370974&scope=bot+applications.commands&permissions=1094645706743)

You can also join Algebra's Official Discord Server: https://discord.gg/uxj2KBVrep

If you still decide to run your own instance of this bot, make sure to keep my credits in and do not steal.

To get started:

1. **Create an application in your Discord Developer Portal and invite it to your server**

  Please reference the docs for steps on doing this. https://discordpy.readthedocs.io/en/stable/discord.html
  
  Make Sure to enable all of the Priveleged Gateway Intents, and Invite your bot to your server as shown in the docs.
 

2. **Download this repo to your local device**

3. **Make sure to install Python 3.8 or higher**

  I am running this on Python 3.11.4, and it works perfectly, but it should work on other versions.

4. **Install Dependencies**

  First, make sure you have pip installed (it should come with your python installation). Next, install all of the dependencies with: `pip install -U -r requirements.txt`

  You will also need ffmpeg for the music bot. You can install it [here.](https://github.com/BtbN/FFmpeg-Builds/releases) Download the proper zip for your OS, and extract the folder. All you need to do is go to the bin folder inside, and take the ffmpeg.exe file and put it into your bot's directory.

5. **Set up config.json**

  Modify the config.json.template file with all the requried information that is listed. Make sure to rename the file to just "config.json" when finished. 
  
  Don't forget to remove all the instructions inside of the file.

6. **Once all of this is done, you should be able to run the bot by running algebra.py**

Navigate to your primary directory where you installed the repo and run: `python algebra.py`


