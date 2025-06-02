#!/usr/bin/env python3
# Copyright 2019-2020 minneyar
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
# disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
# following disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Use this script but also see to the fact that the pypresence is dev version
# pip install https://github.com/qwertyquerty/pypresence/archive/master.zip --break-system-packages

import logging
import struct
import sys
import time

import dbus
import pypresence

# Any of the keys in Clementine's metadata are valid here, but note that colons
# will be replaced with dashes.
# To see a list of keys, play a song and run:
# qdbus org.mpris.MediaPlayer2.clementine /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Get \
#     org.mpris.MediaPlayer2.Player Metadata
DETAILS_STRING = "{xesam-title} ({xesam-album})"
CLIENT_ID = 647617680072900608


class PresenceUpdater:
    def __init__(self):
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing.")

        self.bus = dbus.SessionBus()
        self.client = pypresence.Presence(CLIENT_ID)
        self.player = None
        self.prop_iface = None
        self.last_yt_id = None

    def run(self):
        while True:
            try:
                if not self.prop_iface:
                    self.logger.info("Connecting to Clementine.")
                    self.player = self.bus.get_object(
                        "org.mpris.MediaPlayer2.clementine", "/org/mpris/MediaPlayer2"
                    )
                    self.prop_iface = dbus.Interface(
                        self.player, dbus_interface="org.freedesktop.DBus.Properties"
                    )

                self.logger.info("Connecting to Discord.")
                self.client.connect()

                self.update_loop()
            except dbus.exceptions.DBusException as e:
                self.logger.warning("Error communicating with Clementine: %s" % str(e))
                self.logger.warning("Reconnecting in 15s.")
                self.player = None
                self.prop_iface = None
                time.sleep(15)
            except (
                pypresence.exceptions.InvalidID,
                ConnectionRefusedError,
                struct.error,
            ) as e:
                self.logger.warning("Error communicating with Discord: %s" % str(e))
                self.logger.warning("Reconnecting in 15s.")
                time.sleep(15)

    def update_loop(self):
        while True:
            self.logger.debug("Reading data from Clementine.")
            try:
                metadata = self.prop_iface.Get(
                    "org.mpris.MediaPlayer2.Player", "Metadata"
                )
                position_s = (
                    self.prop_iface.Get("org.mpris.MediaPlayer2.Player", "Position")
                    / 1000000
                )
                playback_status = self.prop_iface.Get(
                    "org.mpris.MediaPlayer2.Player", "PlaybackStatus"
                )
            except dbus.exceptions.DBusException as e:
                self.client.clear()
                raise e

            time_start = None
            time_end = None

            if playback_status == "Stopped":
                details = None
                self.last_yt_id = None
            else:
                tmp_metadata = dict()
                for key, value in metadata.items():
                    tmp_metadata[key.replace(":", "-")] = value
                try:
                    details = DETAILS_STRING.format(**tmp_metadata)
                except KeyError:
                    self.logger.warning("Error getting song details:", exc_info=True)
                    self.logger.warning(
                        "You should customize the DETAILS_STRING in the script to use "
                        "appropriate metadata for your media."
                    )
                    details = "(Error)"

            if playback_status == "Playing":
                try:
                    length_s = metadata["mpris:length"] / 1000000
                    time_now = time.time()
                    time_start = time_now - position_s
                    time_end = time_start + length_s
                    self.last_yt_id = metadata["xesam:comment"][0].split("=")[1]
                except KeyError:
                    # Some media types may not provide length information; just ignore it
                    pass
            self.logger.debug("Updating Discord.")
            kwargs = {
                "activity_type": 2,
                "state": playback_status,
                "details": details,
                "start": time_start,
                "end": time_end,
                "large_image": (
                    f"https://img.youtube.com/vi/{self.last_yt_id}/maxresdefault.jpg"
                    if self.last_yt_id
                    else "clementine_discord"
                ),
            }
            self.client.update(**kwargs)
            time.sleep(3)

    def close(self):
        self.logger.info("Shutting down.")
        self.client.close()


if __name__ == "__main__":
    updater = PresenceUpdater()
    try:
        updater.run()
    finally:
        updater.close()
