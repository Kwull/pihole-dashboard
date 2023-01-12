#!/usr/bin/env python3

# pihole-dashboard
# Copyright (C) 2021  santoru
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import subprocess
import socket
from time import localtime, strftime
import urllib.request
import json
import os
import sys
import hashlib
import netifaces as ni
from waveshare_epd import epd2in13_V2
from PIL import Image, ImageFont, ImageDraw

if os.geteuid() != 0:
    sys.exit("You need root permissions to access E-Ink display, try running with sudo!")

INTERFACE = "wlan0"
PIHOLE_1_PORT = 85
PIHOLE_1_ADDR = "192.168.1.250"

PIHOLE_2_PORT = 80
PIHOLE_2_ADDR = "192.168.68.250"

OUTPUT_STRING = ""
FILENAME = "/tmp/.pihole-dashboard-output"

font_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'font')
font_name = os.path.join(font_dir, "font.ttf")
font16 = ImageFont.truetype(font_name, 16)
font12 = ImageFont.truetype(font_name, 12)

epd = epd2in13_V2.EPD()
epd.init(epd.FULL_UPDATE)


def valid_ip(address):
    try:
        socket.inet_aton(address)
        return True
    except:
        return False


def draw_dashboard(status_string, out_string=None):

    image = Image.new("1", (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)

    # Get Time
    t = strftime("%H:%M:%S", localtime())
    time_string = "Updated: {}".format(t)

    draw.rectangle([(0, 105), (250, 122)], fill=0)
    if out_string is not None:
        draw.text((0, 0), out_string, font=font16, fill=0)
    draw.text((5, 106), status_string, font=font12, fill=1)
    draw.text((150, 106), time_string, font=font12, fill=1)
    epd.display(epd.getbuffer(image))


def update():
    url = "http://{}:{}/admin/api.php".format(PIHOLE_1_ADDR, PIHOLE_1_PORT)
    r1 = json.load(urllib.request.urlopen(url))
    
    url = "http://{}:{}/admin/api.php".format(PIHOLE_2_ADDR, PIHOLE_2_PORT)
    r2 = json.load(urllib.request.urlopen(url))

    try:
        ip = ni.ifaddresses(INTERFACE)[ni.AF_INET][0]['addr']
    except KeyError:
        ip_str = "[×] Can't connect to Wi-Fi"
        ip = ""

    if "unique_clients" not in r1 or "unique_clients" not in r2:
        output_string = "Error from API.\nRun pihole-dashboard-draw\nfor details."
        draw_dashboard('Error', output_string)
        output_error = "API Response: {}\n {}".format(r1, r2)
        sys.exit(output_error)
       
    dns_queries_today_1 = r1['dns_queries_today']
    dns_queries_today_2 = r2['dns_queries_today']
    
    ads_blocked_today_1 = r1['ads_blocked_today']
    ads_blocked_today_2 = r2['ads_blocked_today']
    
    ads_percentage_today_1 = r1['ads_percentage_today']
    ads_percentage_today_2 = r2['ads_percentage_today']
    
    domains_being_blocked_1 = r1['domains_being_blocked']
    domains_being_blocked_2 = r2['domains_being_blocked']
    
    queries_cached_1 = r1['queries_cached']
    queries_cached_2 = r2['queries_cached']
    
    status_1 = r1['status']
    status_2 = r2['status']
    
    OUTPUT_STRING = "[✓] Total Queries: {}, (1) {} / (2) {}".format(dns_queries_today_1+dns_queries_today_2, dns_queries_today_1, dns_queries_today_2)
    OUTPUT_STRING = OUTPUT_STRING + "\n" + "[✓] Queries Cached: {}, (1) {} / (2) {}".format( queries_cached_1+queries_cached_2, queries_cached_1, ads_percentage_today_2)
    OUTPUT_STRING = OUTPUT_STRING + "\n" + "[×] Queries Blocked: {}, (1) {} / (2) {}".format(ads_blocked_today_1+ads_blocked_today_2, ads_blocked_today_1, ads_blocked_today_2)
    OUTPUT_STRING = OUTPUT_STRING + "\n" + "[×] Percent Blocked: (1) {:.2%} / (2) {:.2%}".format(ads_percentage_today_1, ads_percentage_today_2)
    OUTPUT_STRING = OUTPUT_STRING + "\n" + "[×] Blocklist: (1) {} / (2) {}".format(domains_being_blocked_1, domains_being_blocked_2)

    STATUS_STRING = "(1) {} / (2) {}".format(status_1, status_2)
    
    hash_string = hashlib.sha1((OUTPUT_STRING+STATUS_STRING).encode('utf-8')).hexdigest()
    try:
        hash_file = open(FILENAME, "r+")

    except FileNotFoundError:
        os.mknod(FILENAME)
        hash_file = open(FILENAME, "r+")

    file_string = hash_file.read()
    if file_string != hash_string:
        hash_file.seek(0)
        hash_file.truncate()
        hash_file.write(hash_string)
        draw_dashboard(STATUS_STRING, OUTPUT_STRING)
