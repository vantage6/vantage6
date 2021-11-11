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
            '\nSee the complete release notes [here](https://docs.vantage6.ai/release-notes-1/2-harukas)\n\n'
            'To upgrade:'
            '```'
            f'pip install vantage6=={version}'
            '```'
            '\n\n'
            f'_{notes}_'
        )

        repositories = (
            "[vantage6-master](http://github.com/iknl/vantage6-master)\n"
            "[vantage6](http://github.com/iknl/vantage6)\n"
            "[vantage6-client](http://github.com/iknl/vantage6-client)\n"
            "[vantage6-common](http://github.com/iknl/vantage6-common)\n"
            "[vantage6-node](http://github.com/iknl/vantage6-node)\n"
            "[vantage6-server](http://github.com/iknl/vantage6-server)"
        )

        documentation = (
            '[latest release notes](https://docs.vantage6.ai/release-notes-1/2-harukas)\n'
            '[installation instructions](https://docs.vantage6.ai/installation/preliminaries)\n'
            '[How to contribute](https://docs.vantage6.ai/how-to-contribute/how-to-contribute)'
        )

        links = (
            '[harbor](https://harbor.vantage6.ai)\n'
            '[harbor2](https://harbor2.vantage6.ai)\n'
            '[Project website](https://vantage6.ai)\n'
            '[Build status](https://travis-ci.org/github/IKNL)'
        )

        embed=Embed(title=f"Release {version}", url="https://pypi.org", description=description, color=0x0593ff)
        embed.set_author(name="Frank Martin", icon_url="https://secure.gravatar.com/avatar/70ec8a99cb53dda559c7b191e24f3559?size=35")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/789852327623786508/790610154491478076/train.png")
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