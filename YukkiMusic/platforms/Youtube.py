#
# Copyright (C) 2021-2022 by TeamYukki@Github, < https://github.com/TeamYukki >.
#
# This file is part of < https://github.com/TeamYukki/YukkiMusicBot > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/TeamYukki/YukkiMusicBot/blob/master/LICENSE >
#
# All rights reserved.
#
# Fix bug dan update https://github.com/dlrmas
#

import asyncio
import glob
import json
import os
import random
import re
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

import config
from YukkiMusic.logging import LOGGER
from YukkiMusic.utils.database import is_on_off
from YukkiMusic.utils.formatters import time_to_seconds


def get_cookie_file():
    """Get a random cookie file from cookies folder"""
    folder_path = os.path.join(os.getcwd(), "cookies")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return None
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    if not txt_files:
        return None
    cookie_file = random.choice(txt_files)
    return cookie_file


def get_ytdl_options(extra_opts: dict = None) -> dict:
    """Get yt-dlp options with cookie support"""
    opts = {
        "geo_bypass": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
    }
    cookie_file = get_cookie_file()
    if cookie_file:
        opts["cookiefile"] = cookie_file
    if extra_opts:
        opts.update(extra_opts)
    return opts


async def check_file_size(link: str) -> Union[int, None]:
    """Check file size before downloading"""
    cookie_file = get_cookie_file()
    cmd = ["yt-dlp", "-J", link]
    if cookie_file:
        cmd.insert(1, "--cookies")
        cmd.insert(2, cookie_file)
    
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="ignore")[:500]
        LOGGER(__name__).error(f"yt-dlp error: {error_msg}")
        return None
    
    try:
        info = json.loads(stdout.decode())
        formats = info.get("formats", [])
        total_size = sum(f.get("filesize", 0) or 0 for f in formats)
        return total_size
    except Exception as e:
        LOGGER(__name__).error(f"Error parsing file size: {e}")
        return None


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if re.search(self.regex, link):
            return True
        else:
            return False

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            if str(duration_min) == "None":
                duration_sec = 0
            else:
                duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
        return title

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            duration = result["duration"]
        return duration

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        return thumbnail

    async def video(self, link: str, videoid: Union[bool, str] = None):
        """
        Get video stream URL for py-tgcalls.
        Returns the YouTube URL directly - py-tgcalls has built-in yt-dlp 
        integration that handles video extraction automatically.
        """
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        LOGGER(__name__).info(f"Returning YouTube URL for video streaming: {link}")
        return 1, link

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        
        cookie_file = get_cookie_file()
        cookie_opt = f"--cookies {cookie_file}" if cookie_file else ""
        
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist {cookie_opt} --playlist-end {limit} --skip-download {link}"
        )
        try:
            result = playlist.split("\n")
            for key in result:
                if key == "":
                    result.remove(key)
        except:
            result = []
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        ytdl_opts = get_ytdl_options()
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r["formats"]:
                try:
                    str(format["format"])
                except:
                    continue
                if "dash" not in str(format["format"]).lower():
                    try:
                        format["format"]
                        format["filesize"]
                        format["format_id"]
                        format["ext"]
                        format["format_note"]
                    except:
                        continue
                    formats_available.append(
                        {
                            "format": format["format"],
                            "filesize": format["filesize"],
                            "format_id": format["format_id"],
                            "ext": format["ext"],
                            "format_note": format["format_note"],
                            "yturl": link,
                        }
                    )
        return formats_available, link

    async def slider(
        self,
        link: str,
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_optssx = get_ytdl_options({
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
            })
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = get_ytdl_options({
                "format": "bestvideo[height<=?720][width<=?1280][ext=mp4]+bestaudio[ext=m4a]/best[height<=?720][ext=mp4]/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "merge_output_format": "mp4",
            })
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.mp4")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def song_video_dl():
            # Use format_id with fallback to best available
            if format_id and format_id != "best":
                formats = f"{format_id}+bestaudio/best[ext=mp4]/best"
            else:
                formats = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            fpath = f"downloads/{title}.mp4"
            ydl_optssx = get_ytdl_options({
                "format": formats,
                "outtmpl": fpath,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            })
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])
            return fpath

        def song_audio_dl():
            fpath = f"downloads/{title}.mp3"
            # Use format_id with fallback to best audio
            if format_id and format_id not in ["140", "best"]:
                audio_format = f"{format_id}/bestaudio/best"
            else:
                audio_format = "bestaudio/best"
            ydl_optssx = get_ytdl_options({
                "format": audio_format,
                "outtmpl": fpath,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            })
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])
            return fpath

        if songvideo:
            fpath = await loop.run_in_executor(None, song_video_dl)
            return fpath
        elif songaudio:
            fpath = await loop.run_in_executor(None, song_audio_dl)
            return fpath
        elif video:
            # For py-tgcalls 2.x, always download video for better compatibility
            # Direct streaming from YouTube HLS URLs does not work properly
            # because py-tgcalls cannot parse video track from HLS manifests
            direct = True
            downloaded_file = await loop.run_in_executor(None, video_dl)
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        return downloaded_file, direct
