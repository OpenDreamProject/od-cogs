import discord
from redbot.core import app_commands

from odcompile.utils.logger import log
from odcompile.utils.misc import cleanupCode
from odcompile.utils.misc import splitArgs
from odcompile.utils.regex import INCLUDE_PATTERN
from odcompile.utils.relay import processCode


@app_commands.guild_only()
@app_commands.context_menu(name="Compile with OD")
async def compileMessage(interaction: discord.Interaction, compile_message: discord.Message):
    cog = interaction.client.get_cog("ODCompile")

    cleaned_input = splitArgs(args=compile_message.content, strict_args=True)

    code = cleanupCode(cleaned_input["code"])
    if code is None:
        return await interaction.response.send_message("Your code has to be in a code block!")
    if INCLUDE_PATTERN.search(code) is not None:
        return await interaction.response.send_message("You can't have any `#include` statements in your code.")

    log.debug(f"Sending code to the listener to be compiled:\n{code}")
    await interaction.response.defer(thinking=True, ephemeral=False)
    embed = await processCode(
        self=cog,
        code=code,
        args=cleaned_input["args"],
        build_config="Release",
        parsed_output=cleaned_input["parsed"],
    )
    return await interaction.followup.send(
        content=f"Compiled from {compile_message.jump_url}", embed=embed, ephemeral=False
    )
