from asyncio import get_event_loop

from redbot.core import checks
from redbot.core import commands
from redbot.core.config import Config

from odcompile.utils.logger import log
from odcompile.utils.misc import cleanupCode
from odcompile.utils.misc import splitArgs
from odcompile.utils.misc import versionCheck
from odcompile.utils.regex import INCLUDE_PATTERN
from odcompile.utils.relay import processCode


class ODCompile(commands.Cog):
    """A discord compiler for OpenDream"""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, 32175847454, force_registration=True)

        default_config = {"listener_url": "http://localhost:5000", "config_version": None}

        self.config.register_global(**default_config)
        self.loop = get_event_loop()
        self.loop.create_task(versionCheck(self))

    @commands.group()
    @checks.is_owner()
    async def odcompileset(self, ctx):
        """
        DM Compiler settings
        """
        pass

    @odcompileset.command()
    async def listener(self, ctx, url: str = None):
        """
        Set the base URL for the listener, DO NOT include `/compile`

        Should be similar to: http://localhost:5000
        """

        try:
            url = url.rstrip("/")
            await self.config.listener_url.set(url)
            await ctx.send(f"Listener URL set to: {url}")
        except (ValueError, KeyError, AttributeError):
            await ctx.send("There was an error setting the listener's URL. Please check your entry and try again.")

    @commands.command()
    async def odcompile(self, ctx, *, input: str):
        """
        Compile and run DM code

        This command will attempt to compile and execute given DM code. It will respond with the full compile log along with any outputs given during runtime. If there are any errors during compilation, the bot will respond with a list provided by OpenDream.

        Short one-liners can be provided in basic code-markdown, for example:
        `world.log << "Hello, World!"`

        Multi-line or explicit code must be contained within a codeblock, for example:
        ```c
        world.log << 'Hello,'
        world.log << "World!"
        ```
        If you're using multiple functions, or if your code requires indentation, you must define a `/proc/main()` as shown below.
        ```c
        /proc/example()
            world.log << "I'm an example function!"

        /proc/main()
            example()
        ```
        **Arguments**
        You can pass extra command line arguments to the compiler by adding them before the codeblock (e.g. `--version=123.456`).

        Adding `--no-parsing` before the codeblock will provide the full execution output instead of a parsed version.

        If you'd like to compile using the Debug build of OpenDream use `[p]odcompiledebug`

        __Code will always be compiled with the latest version of OpenDream__
        """  # noqa: E501
        cleaned_input = splitArgs(args=input)

        code = cleanupCode(cleaned_input["code"])
        if code is None:
            return await ctx.send("Your code has to be in a code block!")
        if INCLUDE_PATTERN.search(code) is not None:
            return await ctx.send("You can't have any `#include` statements in your code.")

        message = await ctx.send("Compiling. If there have been any updates, this could take a moment....")
        log.debug(f"Sending code to the listener to be compiled:\n{code}")

        async with ctx.typing():
            embed = await processCode(
                self=self,
                code=code,
                args=cleaned_input["args"],
                build_config="Release",
                parsed_output=cleaned_input["parsed"],
            )
            await ctx.send(embed=embed)
            return await message.delete()

    @commands.command()
    async def odcompiledebug(self, ctx, *, input: str):
        """
        Compile and run DM code with OpenDream's Debug build configuration
        """
        cleaned_input = splitArgs(args=input)

        code = cleanupCode(cleaned_input["code"])
        if code is None:
            return await ctx.send("Your code has to be in a code block!")
        if INCLUDE_PATTERN.search(code) is not None:
            return await ctx.send("You can't have any `#include` statements in your code.")

        message = await ctx.send("Compiling. If there have been any updates, this could take a moment....")
        log.debug(f"Sending code to the listener to be compiled:\n{code}")

        async with ctx.typing():
            embed = await processCode(
                self=self,
                code=code,
                args=cleaned_input["args"],
                build_config="Debug",
                parsed_output=cleaned_input["parsed"],
            )
            await ctx.send(embed=embed)
            return await message.delete()
