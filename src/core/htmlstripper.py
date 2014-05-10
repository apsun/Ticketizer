# -*- coding: utf-8 -*-
#
# This file is part of Ticketizer.
# Copyright (c) 2014 Andrew Sun <youlosethegame@live.com>
#
# Ticketizer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ticketizer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ticketizer.  If not, see <http://www.gnu.org/licenses/>.
import html
from html.parser import HTMLParser


class TagStripper(HTMLParser):
    def __init__(self):
        super(TagStripper, self).__init__()
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def handle_entityref(self, name):
        self.text.append(html.unescape("&{0};".format(name)))

    def get_data(self):
        return "".join(self.text)


def strip_html(text):
    s = TagStripper()
    s.feed(text)
    return s.get_data()