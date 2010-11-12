# -*- coding: utf-8 -*-
# Copyright 2008, 2009 Mr.Z-man

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

import cookielib
import api
import urllib
import re
import time
import os
from urlparse import urlparse
try:
	import cPickle as pickle
except:
	import pickle

class WikiError(Exception):
	"""Base class for errors"""

class BadTitle(WikiError):
	"""Invalid title"""
	
class NoPage(WikiError):
	"""Non-existent page"""

class EditError(WikiError):
	"""Problem with edit request"""

class Namespace(int):
	"""
	Class for namespace 'constants'
	Names are based on canonical (non-localized) names
	This functions as an integer in every way, except that the OR operator ( | )
	is overridden to produce a string namespace list for use in API queries
	wikiobj.NS_MAIN|wikiobj.NS_USER|wikiobj.NS_PROJECT returns '0|2|4'
	"""
	def __or__(self, other):
		return '|'.join([str(self), str(other)])
	
	def __ror__(self, other):
		return '|'.join([str(other), str(self)])

VERSION = '1.1.1'
		
class Wiki:
	"""A Wiki site"""

	def __init__(self, url="http://en.wikipedia.org/w/api.php"):
		"""
		url - A URL to the site's API, defaults to en.wikipedia
		"""
		self.apibase = url
		self.cookies = WikiCookieJar()
		self.username = ''
		self.maxlag = 5
		self.maxwaittime = 120
		self.useragent = "python-wikitools/%s" % VERSION
		self.cookiepath = ''
		self.limit = 500
		self.siteinfo = {}
		self.namespaces = {}
		self.NSaliases = {}
		urlbits = urlparse(self.apibase)
		self.domain = '://'.join([urlbits.scheme, urlbits.netloc])
		try:
			self.setSiteinfo()
		except api.APIError: # probably read-restricted
			pass
	
	def setSiteinfo(self):
		"""Retrieves basic siteinfo
		
		Called when constructing,
		or after login if the first call failed
		
		"""
		params = {'action':'query',
			'meta':'siteinfo',
			'siprop':'general|namespaces|namespacealiases',
		}
		if self.maxlag < 120:
			params['maxlag'] = 120
		req = api.APIRequest(self, params)
		info = req.query()
		sidata = info['query']['general']
		for item in sidata:
			self.siteinfo[item] = sidata[item]
		nsdata = info['query']['namespaces']
		for ns in nsdata:
			nsinfo = nsdata[ns]
			self.namespaces[nsinfo['id']] = nsinfo
			if ns != "0":
				attr = "NS_%s" % (nsdata[ns]['canonical'].replace(' ', '_').upper())
			else:
				attr = "NS_MAIN"
			setattr(self, attr, Namespace(ns))			
		nsaliasdata = info['query']['namespacealiases']
		if nsaliasdata:
			for ns in nsaliasdata:
				self.NSaliases[ns['*']] = ns['id']
		if not 'writeapi' in sidata:
			print "WARNING: Write-API not enabled, you will not be able to edit"
		version = re.search("\d\.(\d\d)", self.siteinfo['generator'])
		if not int(version.group(1)) >= 13: # Will this even work on 13?
			print "WARNING: Some features may not work on older versions of MediaWiki"
		return self
	
	def login(self, username, password=False, remember=False, force=False, verify=True, domain=None):
		"""Login to the site
		
		remember - saves cookies to a file - the filename will be:
		hash(username - apibase).cookies
		the cookies will be saved in the current directory, change cookiepath
		to use a different location
		force - forces login over the API even if a cookie file exists 
		and overwrites an existing cookie file if remember is True
		verify - Checks cookie validity with isLoggedIn()
		domain - domain name, required for some auth systems like LDAP
		
		"""
		if not force:
			try:	
				cookiefile = self.cookiepath + str(hash(username+' - '+self.apibase))+'.cookies'
				self.cookies.load(self, cookiefile, True, True)
				self.username = username
				if not verify or self.isLoggedIn(self.username):
					return True
			except:
				pass
		if not password:
			from getpass import getpass
			password = getpass()
		def loginerror(info):
			try:
				print info['login']['result']
			except:
				print info['error']['code']
				print info['error']['info']
			return False
		data = {
			"action" : "login",
			"lgname" : username,
			"lgpassword" : password,
		}
		if domain is not None:
			data["lgdomain"] = domain
		if self.maxlag < 120:
			data['maxlag'] = 120
		req = api.APIRequest(self, data)
		info = req.query()
		if info['login']['result'] == "Success":
			self.username = username
		elif info['login']['result'] == "NeedToken":
			req.changeParam('lgtoken', info['login']['token'])
			info = req.query()
			if info['login']['result'] == "Success":
				self.username = username
			else:
				return loginerror(info)
		else:
			return loginerror(info)
		if not self.siteinfo:
			self.setSiteinfo()
		params = {
			'action': 'query',
			'meta': 'userinfo',
			'uiprop': 'rights',
		}
		if self.maxlag < 120:
			params['maxlag'] = 120
		req = api.APIRequest(self, params)
		info = req.query()
		user_rights = info['query']['userinfo']['rights']
		if 'apihighlimits' in user_rights:
			self.limit = 5000
		if remember:
			cookiefile = self.cookiepath + str(hash(self.username+' - '+self.apibase))+'.cookies'
			self.cookies.save(self, cookiefile, True, True)
		if self.useragent == "python-wikitools/%s" % VERSION:
			self.useragent = "python-wikitools/%s (User:%s)" % (VERSION, self.username)
		return True
	
	def logout(self):
		params = { 'action': 'logout' }
		if self.maxlag < 120:
			params['maxlag'] = 120
		cookiefile = self.cookiepath + str(hash(self.username+' - '+self.apibase))+'.cookies'
		try:
			os.remove(cookiefile)
		except:
			pass
		req = api.APIRequest(self, params, write=True)
		# action=logout returns absolutely nothing, which json.loads() treats as False
		# causing APIRequest.query() to get stuck in a loop
		req.opener.open(req.request)
		self.cookies = WikiCookieJar()
		self.username = ''
		self.maxlag = 5
		self.useragent = "python-wikitools/%s" % VERSION
		self.limit = 500
		return True
		
	def isLoggedIn(self, username = False):
		"""Verify that we are a logged in user
		
		username - specify a username to check against
		
		"""
		
		data = {
			"action" : "query",
			"meta" : "userinfo",
		}
		if self.maxlag < 120:
			data['maxlag'] = 120
		req = api.APIRequest(self, data)
		info = req.query()
		if info['query']['userinfo']['id'] == 0:
			return False
		elif username and info['query']['userinfo']['name'] != username:
			return False
		else:
			return True
	
	def setMaxlag(self, maxlag = 5):
		"""Set the maximum server lag to allow
		
		If the lag is > the maxlag value, all requests will wait
		Setting to a negative number will disable maxlag checks
		
		"""
		try:
			int(maxlag)
		except:
			raise WikiError("maxlag must be an integer")
		self.maxlag = int(maxlag)
		return self.maxlag
		
	def setUserAgent(self, useragent):
		"""Function to set a different user-agent"""
		self.useragent = str(useragent)
		return self.useragent

	def __eq__(self, other):
		if not isinstance(other, Wiki):
			return False
		if self.apibase == other.apibase:
			return True
		return False
	def __ne__(self, other):
		if not isinstance(other, Wiki):
			return True
		if self.apibase == other.apibase:
			return False
		return True
		
	def __str__(self):
		if self.username:
			user = ' - using User:'+self.username
		else:
			user = ' - not logged in'
		return self.domain + user
	
	def __repr__(self):
		if self.username:
			user = ' User:'+self.username
		else:
			user = ' not logged in'
		return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(self.apibase)+user+">"
		
		

class CookiesExpired(WikiError):
	"""Cookies are expired, needs to be an exception so login() will use the API instead"""

class WikiCookieJar(cookielib.FileCookieJar):
	def save(self, site, filename=None, ignore_discard=False, ignore_expires=False):
		if not filename:
			filename = self.filename
		old_umask = os.umask(0077)
		f = open(filename, 'w')
		f.write('')
		content = ''
		for c in self:
			if not ignore_discard and c.discard:
				continue
			if not ignore_expires and c.is_expired:
				continue
			cook = pickle.dumps(c, 2)
			f.write(cook+'|~|')
		content+=str(int(time.time()))+'|~|' # record the current time so we can test for expiration later
		content+='site.limit = %d;' % (site.limit) # This eventially might have more stuff in it
		f.write(content)
		f.close()
		os.umask(old_umask)
	
	def load(self, site, filename, ignore_discard, ignore_expires):
		f = open(filename, 'r')
		cookies = f.read().split('|~|')
		saved = cookies[len(cookies)-2]
		if int(time.time()) - int(saved) > 1296000: # 15 days, not sure when the cookies actually expire...
			f.close()
			os.remove(filename)
			raise CookiesExpired
		sitedata = cookies[len(cookies)-1]
		del cookies[len(cookies)-2]
		del cookies[len(cookies)-1]
		for c in cookies:
			cook = pickle.loads(c)
			if not ignore_discard and cook.discard:
				continue
			if not ignore_expires and cook.is_expired:
				continue
			self.set_cookie(cook)
		exec sitedata
		f.close()
	
