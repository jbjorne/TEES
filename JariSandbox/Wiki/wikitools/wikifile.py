# -*- coding: utf-8 -*-
# Copyright 2009 Mr.Z-man

# This file is part of wikitools.
# wikitools is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
 
# wikitools is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
 
# You should have received a copy of the GNU General Public License
# along with wikitools.  If not, see <http://www.gnu.org/licenses/>.

import wiki
import page
import api
import urllib2

class FileDimensionError(wiki.WikiError):
	"""Invalid dimensions"""
	
class UploadError(wiki.WikiError):
	"""Error during uploading"""

class File(page.Page):
	"""A file on the wiki"""
	def __init__(self, wiki, title, check=True, followRedir=False, section=False, sectionnumber=False):
		"""	
		wiki - A wiki object
		title - The page title, as a string or unicode object
		check - Checks for existence, normalizes title, required for most things
		followRedir - follow redirects (check must be true)
		section - the section name
		sectionnumber - the section number
		pageid - pageid, can be in place of title
		""" 
		page.Page.__init__(self, wiki, title, check, followRedir, section, sectionnumber)
		if self.namespace != 6:
			self.setNamespace(6, check)
		self.usage = []
		self.history = []
		
	def getHistory(self, force=False):
		if self.history and not force:
			return self.history
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'imageinfo',
			'iilimit': self.site.limit,
		}
		if self.pageid > 0:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title	
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.history = response['query']['pages'][str(self.pageid)]['imageinfo']
		return self.history
			
	def getUsage(self, titleonly=False, force=False, namespaces=False):
		"""Gets a list of pages that use the file
		
		titleonly - set to True to only create a list of strings,
		else it will be a list of Page objects
		force - reload the list even if it was generated before
		namespaces - List of namespaces to restrict to (queries with this option will not be cached)
		
		"""
		if self.usage and not reload:
			if titleonly:
				if namespaces is not False:
					return [p.title for p in self.usage if p.namespace in namespaces]
				else:
					return [p.title for p in self.usage]
			if namespaces is False:
				return self.usage
			else:
				return [p for p in self.usage if p.namespace in namespaces]
		else:
			ret = []
			usage = []
			for title in self.__getUsageInternal(namespaces):
				usage.append(title)
				if titleonly:
					ret.append(title.title)
			if titleonly:
				return ret
			if namespaces is False:
				self.usage = usage
			return usage
	
	def getUsageGen(self, titleonly=False, force=False, namespaces=False):
		"""Generator function for pages that use the file
		
		titleonly - set to True to return strings,
		else it will return Page objects
		force - reload the list even if it was generated before
		namespaces - List of namespaces to restrict to (queries with this option will not be cached)
		
		"""
		if self.usage and not reload:
			for title in self.usage:
				if namespaces is False or title.namespace in namespaces:
					if titleonly:
						yield title.title
					else:
						yield title
		else:
			if namespaces is False:
				self.usage = []
			for title in self.__getUsageInternal():
				if namespaces is False:
					self.usage.append(title)
				if titleonly:
					yield title.title
				else:
					yield title
				
	def __getUsageInternal(self, namespaces=False):
		params = {'action':'query',
			'list':'imageusage',
			'iutitle':self.title,
			'iulimit':self.site.limit,
		}
		if namespaces is not False:
			params['iunamespace'] = '|'.join([str(ns) for ns in namespaces])
		while True:
			req = api.APIRequest(self.site, params)
			data = req.query(False)
			for item in data['query']['imageusage']:
				yield page.Page(self.site, item['title'], check=False, followRedir=False)
			try:
				params['iucontinue'] = data['query-continue']['imageusage']['iucontinue']
			except:
				break 
		
	def __extractToList(self, json, stuff):
		list = []
		if stuff in json['query']:
			for item in json['query'][stuff]:
				list.append(item['title'])
		return list
	
	def download(self, width=False, height=False, location=False):
		"""Download the image to a local file
		
		width/height - set width OR height of the downloaded image
		location - set the filename to save to. If not set, the page title
		minus the namespace prefix will be used and saved to the current directory
		
		"""
		if self.pageid == 0:
			self.setPageInfo()
		params = {'action':'query',
			'prop':'imageinfo',
			'iiprop':'url'
		}
		if width and height:
			raise DimensionError("Can't specify both width and height")
		if width:
			params['iiurlwidth'] = width
		if height:
			params['iiurlheight'] = height
		if self.pageid != 0:
			params['pageids'] = self.pageid
		elif self.title:
			params['titles'] = self.title
		else:
			self.setPageInfo()
			if not self.exists: # Non-existant files may be on a shared repo (e.g. commons)
				params['titles'] = self.title
			else:
				params['pageids'] = self.pageid
		req = api.APIRequest(self.site, params)
		res = req.query(False)
		key = res['query']['pages'].keys()[0]
		url = res['query']['pages'][key]['imageinfo'][0]['url']
		if not location:
			location = self.title.split(':', 1)[1]
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.site.cookies))
		headers = { "User-agent": self.site.useragent }
		request = urllib2.Request(url, None, headers)
		data = opener.open(request)
		f = open(location, 'wb', 0)
		f.write(data.read())
		f.close()
		return location
		
	def upload(self, fileobj=None, comment='', url=None, ignorewarnings=False, watch=False):
		"""Upload a file, requires the "poster" module
		
		fileobj - A file object opened for reading
		comment - The log comment, used as the inital page content if the file 
		doesn't already exist on the wiki
		url - A URL to upload the file from, if allowed on the wiki
		ignorewarnings - Ignore warnings about duplicate files, etc.
		watch - Add the page to your watchlist
		
		"""
		if not api.canupload and fileobj:
			raise UploadError("The poster module is required for file uploading")
		if not fileobj and not url:
			raise UploadError("Must give either a file object or a URL")
		if fileobj and url:
			raise UploadError("Cannot give a file and a URL")
		params = {'action':'upload',
			'comment':comment,
			'filename':self.unprefixedtitle,
			'token':self.getToken('edit') # There's no specific "upload" token
		}
		if url:
			params['url'] = url
		else:
			params['file'] = fileobj
		if ignorewarnings:
			params['ignorewarnings'] = ''
		if watch:
			params['watch'] = ''
		req = api.APIRequest(self.site, params, write=True, multipart=bool(fileobj))
		res = req.query()
		if 'upload' in res and res['upload']['result'] == 'Success':
			self.wikitext = ''
			self.links = []
			self.templates = []
			self.exists = True
		return res
		
			
