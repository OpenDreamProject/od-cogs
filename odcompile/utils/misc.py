import json

from discord import Embed
from packaging.version import parse as parse_version
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.chat_formatting import escape

from odcompile._version import __version__
from odcompile.utils.logger import log
from odcompile.utils.regex import CODE_BLOCK_RE
from odcompile.utils.regex import COMPILER_ERROR_RE
from odcompile.utils.regex import COMPILER_WARNING_RE
from odcompile.utils.regex import SERVER_ENDING_OUTPUT_RE
from odcompile.utils.regex import SERVER_ERROR_RE
from odcompile.utils.regex import SERVER_STARTING_OUTPUT_RE


def cleanupCode(content: str) -> str | None:
    """
    clears those pesky codeblocks
    """
    content = escape(content)
    if content.startswith("`") and content.endswith("`"):
        content = CODE_BLOCK_RE.sub("", content)[1:]
        return content.strip("\n")
    elif content.endswith("`"):
        content = CODE_BLOCK_RE.sub("", content)
        return content.strip("\n")

    return None


def splitArgs(args: str, delimiter: str = "`", strict_args: bool = False) -> dict:
    """
    Take a list of arguments and split them based on the delimiter.

    Returns a dict of arguments
    """
    args_dict = {}

    args = args.split(sep=delimiter, maxsplit=1)
    args_dict["code"] = args[1]
    args_dict["args"] = [arg.replace("\n", "") for arg in args[0].split(" ")]
    log.error(args_dict["args"])
    args_dict["parsed"] = True

    if strict_args:
        args_dict["args"] = [arg for arg in args_dict["args"] if arg.startswith("--")]

    if "--no-parsing" in args_dict["args"]:
        args_dict["parsed"] = False
        args_dict["args"].remove("--no-parsing")

    return args_dict


def getEmbed(logs: json, parsed_output: bool = True) -> Embed:
    """
    Generates a discord embed based on the provided logs
    """
    if "build_error" in logs.keys():
        embed = Embed(title="Unable to build image", description=f"{logs['exception']}", color=0xFF0000)
        return embed

    compile_log = (logs["compiler"][:1200] + "...") if len(logs["compiler"]) > 1200 else logs["compiler"]

    # We need to send a larger sample to the parser to ensure that we properly match our ODC stanza
    # Sending the full output could result in application hangs if the string is too large
    run_log = parseRunOutput(logs["server"][:5000], parsed_output=parsed_output)
    run_log = (run_log[:1200] + "...") if len(run_log) > 1200 else run_log

    compiler_output = box(escape(compile_log, mass_mentions=True, formatting=True))
    execution_output = box(escape(run_log, mass_mentions=True, formatting=True))

    if logs["timeout"]:
        embed = Embed(
            title="Execution timed out (30 seconds)",
            description=f"Compiler Output:\n{compiler_output}\nExecution Output:\n{execution_output}",
            color=0xD3D3D3,
        )
        return embed
    if COMPILER_ERROR_RE.search(compile_log) is not None:
        embed = Embed(
            title="Errors found during compilation!",
            description=f"Compiler Output:\n{compiler_output}",
            color=0xFF0000,
        )
        return embed

    if int(COMPILER_WARNING_RE.search(compile_log).group(1)) > 0:
        embed = Embed(
            title="Warnings found during compilation!",
            description=f"Compiler Output:\n{compiler_output}\nExecution Output:\n{execution_output}",
            color=0xFFCC00,
        )
    elif SERVER_ERROR_RE.search(run_log) is not None:
        embed = Embed(
            title="Errors found during execution!",
            description=f"Compiler Output:\n{compiler_output}\nExecution Output:\n{execution_output}",
            color=0xFF0000,
        )
    else:
        embed = Embed(
            description=f"Compiler Output:\n{compiler_output}\nExecution Output:\n{execution_output}", color=0x00FF00
        )
    return embed


def parseRunOutput(logs: str, parsed_output: bool) -> str:
    """
    Parse the run output to make it a lot more readable
    """
    if parsed_output is True:
        logs = SERVER_STARTING_OUTPUT_RE.sub("", logs)
        logs = SERVER_ENDING_OUTPUT_RE.sub("", logs)
    return logs


async def versionCheck(self) -> None:
    """
    Checks the current config version and triggers actions or sends the owner a notice if needed
    """
    config_version = await self.config.config_version() or "0"

    if config_version == __version__:
        return

    await self.config.config_version.set(__version__)
    log.info(f"Config version updated from {config_version} to {__version__} ")

    if parse_version(config_version) < parse_version("0.2.0"):
        """
        In version 0.2.0 we added version checking which requires
        the base URL to be stored instead of the strict /compile URL.
        """
        listener_url = await self.config.listener_url()
        corrected_url = listener_url.rstrip("/compile")
        await self.config.listener_url.set(corrected_url)
        log.warning(f"Listener url config entry updated to '{corrected_url}' from '{listener_url}'")
