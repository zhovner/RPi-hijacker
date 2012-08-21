#!/bin/bash
/sbin/iwlist $1 scan | /wifid/essid_parse.py | grep -v TP-LINK_BACB62 | sed '1d' | grep Open | sort -n | tail -1 
