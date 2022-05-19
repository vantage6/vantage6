from discord import Embed
# import discord
import os
import click
from discord.ext import tasks, commands

# from vantage6.common import info
# from dotenv import load_dotenv

def info(msg):
    print(msg)

# load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.bot.Bot('$')

class PostUpdates(commands.Cog):

    def __init__(self, bot, version, notes, post_notes):
        self.bot = bot
        self.info = [version, notes, post_notes]
        self.update_community.start()

    @tasks.loop(count=1)
    async def update_community(self):
        info("Ready to send message")
        for channel in self.bot.get_all_channels():
            if channel.name == 'general':
                await channel.send(embed=self.create_embed(*self.info))
                exit()

    @update_community.before_loop
    async def before_printer(self):
        info('Signing in to Discord...')
        await self.bot.wait_until_ready()

    @staticmethod
    def create_embed(version, summary, notes):

        description = (
            ':triangular_flag_on_post: A new **vantage6** release! :triangular_flag_on_post:\n\n'
            f'{summary}'
            '\nSee the complete release notes [here](https://docs.vantage6.ai/about-background/release-notes)\n\n'
            'To upgrade:'
            '```'
            f'pip install vantage6=={version}'
            '```'
            '\n\n'
            f'_{notes}_'
        )

        repositories = (
            "[vantage6](http://github.com/vantage6)"
        )

        documentation = (
            '[Latest release notes](https://docs.vantage6.ai/about-background/release-notes)\n'
            '[Installation instructions](https://docs.vantage6.ai/installation/what-to-install)\n'
            '[How to contribute](https://docs.vantage6.ai/v/petronas/how-to-contribute/how-to-contribute)'
            '[Discourse](https://vantage6.discourse.group/)\n'
        )

        links = (
            '[harbor2](https://harbor2.vantage6.ai)\n'
            '[Project website](https://vantage6.ai)\n'
            '[Build status](https://github.com/vantage6/vantage6/actions)'
        )

        embed=Embed(title=f"Release {version}", url="https://pypi.org", description=description, color=0x0593ff)
        embed.set_author(name="vantage6 Team", icon_url="https://nl.gravatar.com/userimage/193840621/ae1b7b037ec1f7f16e15a75d0ae10b0f.png?size=35")
        embed.set_thumbnail(url="https://github.com/IKNL/guidelines/blob/master/resources/logos/vantage6.png?raw=true")
        embed.add_field(name="Docker Images", value=f"harbor2.vantage6.ai/infrastructure/node:{version} \n harbor2.vantage6.ai/infrastructure/server:{version}", inline=False)
        embed.add_field(name="Documentation", value=documentation, inline=True)
        embed.add_field(name="Github", value=repositories, inline=True)
        embed.add_field(name="Usefull links", value=links, inline=True)
        embed.set_footer(text="Running into issues? Let us know!")

        return embed

@click.command()
@click.option('--version', default=None, help="major.minor.patch.specBuild")
@click.option('--notes', default=None)
@click.option('--post-notes', default=None)
def update_the_community(version, notes, post_notes):

    bot.add_cog(PostUpdates(bot, version, notes, post_notes))
    bot.run(TOKEN)


if __name__ == '__main__':
    update_the_community()