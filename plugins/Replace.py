#!/usr/bin/env python2.7

# Copyright (c) 2014-2016 Marcello Salvati
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

"""
Plugin by @rubenthijssen
"""

import sys
import logging
import time
import re
from plugins.plugin import Plugin
from plugins.CacheKill import CacheKill

mitmf_logger = logging.getLogger('mitmf')

class Replace(CacheKill, Plugin):
	name       = "Replace"
	optname    = "replace"
	desc       = "Replace arbitrary content in HTML content"
	implements = ["handleResponse", "handleHeader", "connectionMade"]
	depends    = ["CacheKill"]
	version    = "0.1"
	has_opts   = True

	def initialize(self, options):
		self.options = options

		self.search_str = options.search_str
		self.replace_str = options.replace_str
		self.regex_file = options.regex_file

		if (self.search_str is None or self.search_str == "") and self.regex_file is None:
			sys.exit("[-] Please provide a search string or a regex file")

		self.regexes = []
		if self.regex_file is not None:
			for line in self.regex_file:
				self.regexes.append(line.strip().split("\t"))

		if self.options.keep_cache:
			self.implements.remove("handleHeader")
			self.implements.remove("connectionMade")

		self.ctable = {}
		self.dtable = {}
		self.mime = "text/html"

	def handleResponse(self, request, data):
		ip, hn, mime = self._get_req_info(request)

		if self._should_replace(ip, hn, mime):

			if self.search_str is not None and self.search_str != "":
				data = data.replace(self.search_str, self.replace_str)
				mitmf_logger.info("%s [%s] Replaced '%s' with '%s'" % (request.client.getClientIP(), request.headers['host'], self.search_str, self.replace_str))

			# Did the user provide us with a regex file?
			for regex in self.regexes:
				try:
					data = re.sub(regex[0], regex[1], data)

					mitmf_logger.info("%s [%s] Occurances matching '%s' replaced with '%s'" % (request.client.getClientIP(), request.headers['host'], regex[0], regex[1]))
				except Exception:
					logging.error("%s [%s] Your provided regex (%s) or replace value (%s) is empty or invalid. Please debug your provided regex(es)" % (request.client.getClientIP(), request.headers['host'], regex[0], regex[1]))

			self.ctable[ip] = time.time()
			self.dtable[ip+hn] = True

			return {'request': request, 'data': data}

		return

	def add_options(self, options):
		options.add_argument("--search-str", type=str, default=None, help="String you would like to replace --replace-str with. Default: '' (empty string)")
		options.add_argument("--replace-str", type=str, default="", help="String you would like to replace.")
		options.add_argument("--regex-file", type=file, help="Load file with regexes. File format: <regex1>[tab]<regex2>[new-line]")
		options.add_argument("--keep-cache", action="store_true", help="Don't kill the server/client caching.")

	def _should_replace(self, ip, hn, mime):
		return mime.find(self.mime) != -1

	def _get_req_info(self, request):
		ip = request.client.getClientIP()
		hn = request.client.getRequestHostname()
		mime = request.client.headers['Content-Type']

		return (ip, hn, mime)
