import yt_dlp
from ytmusicapi import YTMusic, OAuthCredentials
from os import remove, walk
from subprocess import run
from threading import Thread
from time import sleep

client_id = "PUT FROM YT MUSIC SYNCER"
client_secret = "PUT FROM YT MUSIC SYNCER"
ytmusic = YTMusic(
    "/home/sumagnadas/bin/oauth.json",
    oauth_credentials=OAuthCredentials(
        client_id=client_id, client_secret=client_secret
    ),
)
while 1:
    try:
        favePlaylistTracks = ytmusic.get_playlist("PLbQ3f72VAiqRATuJRas5hfRHni8n7plLX")[
            "tracks"
        ]
        gamingPlaylistTracks = ytmusic.get_playlist(
            "PLbQ3f72VAiqSon8LHWDWItfSgTA_1cLqk"
        )["tracks"]
    except Exception:
        run(
            [
                "notify-send",
                "Some error occured in syncing playlist. Sleeping for 10 mins.",
            ]
        )
        sleep(600)
        continue
    gamingPlaylistTracksId = set([track["videoId"] for track in gamingPlaylistTracks])
    favePlaylistTracksId = set([track["videoId"] for track in favePlaylistTracks])
    songsDownloadedinfo = dict()
    n = 1
    files = list(walk("/home/sumagnadas/Music"))
    for name in files[0][2]:
        id = name.split(" ")[0][1:-1]
        songsDownloadedinfo[id] = name

    for name in files[1][2]:
        id = name.split(" ")[0][1:-1]
        songsDownloadedinfo[id] = name

    songsDownloaded = set(songsDownloadedinfo.keys())
    if songsDownloaded != gamingPlaylistTracksId.union(favePlaylistTracksId):
        songsToBeDownloaded = (
            gamingPlaylistTracksId.union(favePlaylistTracksId) - songsDownloaded
        )
        songsToBeDeleted = songsDownloaded - gamingPlaylistTracksId.union(
            favePlaylistTracksId
        )

        if len(songsToBeDownloaded):
            run(["notify-send", f"{len(songsToBeDownloaded)} new songs to download"])
        if len(songsToBeDeleted):
            run(["notify-send", f"{len(songsToBeDeleted)} songs to delete"])

        def delete_songs():
            for id in songsToBeDeleted:
                if songsDownloadedinfo[id] in files[0][2]:
                    remove(f"/home/sumagnadas/Music/{songsDownloadedinfo[id]}")
                else:
                    remove(f"/home/sumagnadas/Music/Gaming/{songsDownloadedinfo[id]}")
                songsDownloadedinfo.pop(id)

        def write_to_file(d):
            if d["status"] == "finished":
                global n
                print(f"{n} songs down {d['filename']}")
                n += 1

        class MyLogger:
            def debug(self, msg):
                pass

            def info(self, msg):
                pass

            def warning(self, msg):
                pass

            def error(self, msg):
                pass

        ydl_fave_opts = {
            "logger": MyLogger(),
            "progress_hooks": [write_to_file],
            "format": "m4a/bestaudio/best",
            "writethumbnail": True,
            "cookiefile": "/home/sumagnadas/bin/cookies.txt",
            "postprocessors": [
                {"key": "FFmpegMetadata"},
                {"key": "EmbedThumbnail"},
            ],
        }
        ydl_gaming_opts = ydl_fave_opts.copy()
        ydl_fave_opts["outtmpl"] = "/home/sumagnadas/Music/(%(id)s) %(title)s.%(ext)s"
        ydl_gaming_opts["outtmpl"] = (
            "/home/sumagnadas/Music/Gaming/(%(id)s) %(title)s.%(ext)s"
        )
        faveURLS = [
            "https://music.youtube.com/watch?v=" + trackId
            for trackId in (songsToBeDownloaded.difference(gamingPlaylistTracksId))
        ]
        gamingURLS = [
            "https://music.youtube.com/watch?v=" + trackId
            for trackId in songsToBeDownloaded.intersection(gamingPlaylistTracksId)
        ]
        delete_songs()
        try:
            if gamingURLS:
                with yt_dlp.YoutubeDL(ydl_gaming_opts) as ydl:
                    error_code = ydl.download(gamingURLS)
            if faveURLS:
                with yt_dlp.YoutubeDL(ydl_fave_opts) as ydl:
                    error_code = ydl.download(faveURLS)
        except Exception:
            run(
                [
                    "notify-send",
                    "Some error occured in syncing playlist. Sleeping for 10 mins.",
                ]
            )
    sleep(600)
