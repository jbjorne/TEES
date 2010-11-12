# -*- coding: utf-8 -*-
# Copyright 2008, 2009 Mr.Z-man,  bjweeks

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

import datetime
import wiki
import api
import urllib
import re
from hashlib import md5

class BadTitle(wiki.WikiError):
	"""Invalid title"""
	
class NoPage(wiki.WikiError):
	"""Non-existent page"""
	
class BadNamespace(wiki.WikiError):
	"""Invalid namespace number"""

class EditError(wiki.WikiError):
	"""Problem with edit request"""

class ProtectError(wiki.WikiError):
	"""Problem with protection request"""

def namespaceDetect(title, site):
	""" Detect the namespace of a given title
	title - the page title
	site - the wiki object the page is on
	"""
	bits = title.split(':', 1)
	if len(bits) == 1 or bits[0] == '':
		return 0
	else:
		nsprefix = bits[0].lower() # wp:Foo and caTEGory:Foo are normalized by MediaWiki
		for ns in site.namespaces:
			if nsprefix == site.namespaces[ns]['*'].lower():
				return int(ns)
		else:
			if site.NSaliases:
				for ns in site.NSaliases:
					if nsprefix == ns.lower():
						return int(site.NSaliases[ns])
	return 0	
	
class Page(object):
	""" A page on the wiki"""

	def __init__(self, site, title=False, check=True, followRedir=True, section=False, sectionnumber=False, pageid=False, namespace=False):
		"""	
		wiki - A wiki object
		title - The page title, as a string or unicode object
		check - Checks for existence, normalizes title, required for most things
		followRedir - follow redirects (check must be true)
		section - the section name
		sectionnumber - the section number
		pageid - pageid, can be in place of title
		namespace - use to set the namespace prefix *if its not already in the title*
		""" 
		# Initialize instance vars from function args
		if not title and not pageid:
			raise wiki.WikiError("No title or pageid given")
		self.site = site
		if pageid:
			self.pageid = int(pageid)
		else:
			self.pageid = 0
		self.followRedir = followRedir
		self.title = title
		self.unprefixedtitle = False # will be set later
		self.urltitle = ''
		self.wikitext = ''
		self.templates = []
		self.links = []
		self.categories = []
		self.exists = True # If we're not going to check, assume it does
		self.protection = {}
		self.namespace = namespace
		
		# Things that need to be done before anything else
		if self.title:
			self.title = self.title.replace('_', ' ')
		if self.namespace:
			if namespace not in self.site.namespaces.keys():
				raise BadNamespace(namespace)
			if self.title:
				self.unprefixedtitle = self.title
				self.title = ':'.join((self.site.namespaces[self.namespace]['*'], self.title.decode('utf8')))
		if self.namespace is 0 and self.title:
			self.unprefixedtitle = self.title		
		# Setting page info with API, should set:
		# pageid, exists, title, unprefixedtitle, namespace
		if check:
			self.setPageInfo()
		else:
			if self.namespace is False and self.title:
				self.namespace = namespaceDetect(self.title, self.site)
				if self.namespace is not 0:
					nsname = self.site.namespaces[self.namespace]['*']
					self.unprefixedtitle = self.title.split(':', 1)[1]
					self.title = ':'.join((nsname, self.unprefixedtitle))
				else:
					self.unprefixedtitle = self.title
					
		if section or sectionnumber is not False:
			self.setSection(section, sectionnumber)
		else:
			self.section = False
		if title:
			if not isinstance(self.title, unicode):
				self.title = unicode(self.title, 'utf-8')
			if not isinstance(self.unprefixedtitle, unicode):
				self.unprefixedtitle = unicode(self.unprefixedtitle, 'utf-8')
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')

	def setPageInfo(self):
		"""Sets basic page info, required for almost everything"""
		followRedir = self.followRedir
		params = {'action':'query'}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		if followRedir:
			params['redirects'] = ''
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.pageid = response['query']['pages'].keys()[0]
		if self.pageid > 0:
			self.exists = True
		if 'missing' in response['query']['pages'][str(self.pageid)]:
			if not self.title:
				# Pageids are never recycled, so a bad pageid with no title will never work
				raise wiki.WikiError("Bad pageid given with no title")
			self.exists = False
		if 'invalid' in response['query']['pages'][str(self.pageid)]:
			raise BadTitle(self.title)
		if 'title' in response['query']['pages'][str(self.pageid)]:
			self.title = response['query']['pages'][str(self.pageid)]['title'].encode('utf-8')
			self.namespace = int(response['query']['pages'][str(self.pageid)]['ns'])
			if self.namespace is not 0:
				self.unprefixedtitle = self.title.split(':', 1)[1]	
			else:
				self.unprefixedtitle = self.title
		if 'invalid' in response['query']['pages'][str(self.pageid)]:
			raise BadTitle(self.title)
		self.pageid = int(self.pageid)
		if self.pageid < 0:
			self.pageid = 0
		return self
		
	def setNamespace(self, newns, recheck=False):
		"""Change the namespace number of a page object
		
		Updates the title with the new prefix
		newns - integer namespace number
		recheck - redo pageinfo checks
		
		"""
		if not newns in self.site.namespaces.keys():
			raise BadNamespace
		if self.namespace == newns:
			return self.namespace
		if self.title:
			if self.namespace != 0:
				bits = self.title.split(':', 1)
				nsprefix = bits[0].lower()
				for ns in self.site.namespaces:
					if nsprefix == self.site.namespaces[ns]['*'].lower():
						self.title = bits[1]
						break
				else:
					if self.site.NSaliases:
						for ns in self.site.NSaliases:
							if nsprefix == ns.lower():
								self.title = bits[1]
								break
			self.namespace = newns
			if self.namespace:
				self.title = self.site.namespaces[self.namespace]['*']+':'+self.title
			self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')
		else:
			self.namespace = newns
		if recheck:
			self.pageid = False
			self.setPageInfo()
		else:
			self.pageid = 0
		self.wikitext = ''
		self.templates = []
		self.links = []
		return self.namespace
		
	def setSection(self, section=None, number=None):
		"""Set a section for the page
		
		section - the section name
		number - the section number
		
		"""
		if section is None and number is None:
			self.section = False
		elif number is not None:
			try:
				self.section = str(int(number))
			except ValueError:
				raise WikiError("Section number must be an int")
		else:
			self.section = self.__getSection(section)
		self.wikitext = ''
		return self.section
	
	def __getSection(self, section):
		if not self.title:
			self.setPageInfo()
		params = {
			'action': 'parse',
			'page':self.title,
			'prop':'sections'
		}
		number = False
		req = api.APIRequest(self.site, params)
		response = req.query()
		for item in response['parse']['sections']:
			if section == item['line'] or section == item['anchor']:
				if item['index'].startswith('T'): # TODO: It would be cool if it set the page title to the template in this case 
					continue
				number = item['index']
				break
		return number
		
	def canHaveSubpages(self):
		"""Is the page in a namespace that allows subpages?"""
		if not self.title:
			self.setPageInfo()
		return 'subpages' in self.site.namespaces[self.namespace]
		
	def isRedir(self):
		"""Is the page a redirect?"""
		params = {'action':'query',
			'redirects':''
		}
		if not self.exists:
			raise NoPage
		if self.pageid != 0 and self.exists:
			params['pageids'] = self.pageid
		elif self.title:
			params['titles'] = self.title
		else:
			self.setPageInfo()
			if self.pageid != 0 and self.exists:
				params['pageids'] = self.pageid
			else:
				raise NoPage
		req = api.APIRequest(self.site, params)
		res = req.query()
		if 'redirects' in res['query']:
			return True
		else:
			return False
	
	def isTalk(self):
		"""Is the page a discussion page?"""
		if not self.title:
			self.setPageInfo()
		return (self.namespace%2==1 and self.namespace >= 0)
		
	def toggleTalk(self, check=True, followRedir=True):
		"""Switch to and from the talk namespaces
		
		Returns a new page object that's either the talk or non-talk
		version of the current page
		
		check and followRedir - same meaning as Page constructor
		
		"""
		if not self.title:
			self.setPageInfo()
		ns = self.namespace
		if ns < 0:
			return False
		nsname = self.site.namespaces[ns]['*']
		if self.isTalk():
			newns = self.site.namespaces[ns-1]['*']
		else:
			newns = self.site.namespaces[ns+1]['*']
		try:
			pagename = self.title.split(nsname+':',1)[1]
		except:
			pagename = self.title
		if newns != '':
			newname = newns+':'+pagename
		else:
			newname = pagename
		return Page(self.site, newname, check, followRedir)						
			
	def getWikiText(self, expandtemplates=False, force=False):
		"""Gets the Wikitext of the page
		
		expandtemplates - expand the templates to wikitext instead of transclusions
		force - load the text even if we already loaded it before
		
		"""
	
		if self.wikitext and not force:
			return self.wikitext
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'revisions',
			'rvprop': 'content|timestamp',
			'rvlimit': '1'
		}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title		
		if expandtemplates:
			params['rvexpandtemplates'] = '1'
		if self.section is not False:
			params['rvsection'] = self.section
		req = api.APIRequest(self.site, params)
		response = req.query(False)
		if self.pageid == 0:
			self.pageid = response['query']['pages'].keys()[0]
		self.wikitext = response['query']['pages'][str(self.pageid)]['revisions'][0]['*'].encode('utf-8')
		self.lastedittime = response['query']['pages'][str(self.pageid)]['revisions'][0]['timestamp']
		return self.wikitext
	
	def getLinks(self, force=False):
		"""Gets a list of all the internal links *on* the page
		
		force - load the list even if we already loaded it before
		
		"""
		if self.links and not force:
			return self.links
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'links',
			'pllimit': self.site.limit,
		}
		if self.pageid > 0:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title	
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.links = []
		if isinstance(response, list): #There shouldn't be more than 5000 links on a page...
			for page in response:
				self.links.extend(self.__extractToList(page, 'links'))
		else:
			self.links = self.__extractToList(response, 'links')
		return self.links
		
	def getProtection(self, force=False):
		"""Returns the current protection status of the page"""
		if self.protection and not force:
			return self.protection
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		params = {
			'action': 'query',
			'prop': 'info',
			'inprop': 'protection',
		}
		if not self.exists or self.pageid <= 0:
			params['titles'] = self.title
		else:
			params['titles'] = self.title
		req = api.APIRequest(self.site, params)
		response = req.query()
		for pr in response['query'].values()[0].values()[0]['protection']:
			if pr['level']: 
				if pr['expiry'] == 'infinity':
					expiry = 'infinity'
				else:
					expiry = datetime.datetime.strptime(pr['expiry'],'%Y-%m-%dT%H:%M:%SZ')
				self.protection[pr['type']] = {
					'expiry': expiry, 
					'level': pr['level']
					}
		return self.protection
	
	def getTemplates(self, force=False):
		"""Gets all list of all the templates on the page
		
		force - load the list even if we already loaded it before
		
		"""	
		if self.templates and not force:
			return self.templates
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'templates',
			'tllimit': self.site.limit,
		}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title	
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.templates = []
		if isinstance(response, list): #There shouldn't be more than 5000 templates on a page...
			for part in response:
				self.templates.extend(self.__extractToList(part, 'templates'))
		else:
			self.templates = self.__extractToList(response, 'templates')
		return self.templates
	
	def getCategories(self, force=False):
		"""Gets all list of all the categories on the page
		
		force - load the list even if we already loaded it before
		
		"""	
		if self.categories and not force:
			return self.categories
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		params = {
			'action': 'query',
			'prop': 'categories',
			'cllimit': self.site.limit,
		}
		if self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title	
		req = api.APIRequest(self.site, params)
		response = req.query()
		self.categories = []
		if isinstance(response, list):
			for part in response:
				self.categories.extend(self.__extractToList(part, 'categories'))
		else:
			self.categories = self.__extractToList(response, 'categories')
		return self.categories
	
	def __extractToList(self, json, stuff):
		list = []
		if self.pageid == 0:
			self.pageid = json['query']['pages'].keys()[0]
		if stuff in json['query']['pages'][str(self.pageid)]:
			for item in json['query']['pages'][str(self.pageid)][stuff]:
				list.append(item['title'])
		return list
	
	def edit(self, *args, **kwargs):
		"""Edit the page
		
		Arguments are a subset of the API's action=edit arguments, valid arguments
		are defined in the validargs set
		To skip the MD5 check, set "skipmd5" keyword argument to True
		http://www.mediawiki.org/wiki/API:Edit_-_Create%26Edit_pages#Parameters
		
		For backwards compatibility:
		'newtext' is equivalent to  'text'
		'basetime' is equivalent to 'basetimestamp'
		
		"""
		validargs = set(['text', 'summary', 'minor', 'notminor', 'bot', 'basetimestamp', 'starttimestamp',
			'recreate', 'createonly', 'nocreate', 'watch', 'unwatch', 'watchlist', 'prependtext', 'appendtext', 
			'section'])			
		# For backwards compatibility
		if 'newtext' in kwargs:
			kwargs['text'] = kwargs['newtext']
			del kwargs['newtext']
		if 'basetime' in kwargs:
			kwargs['basetimestamp'] = kwargs['basetime']
			del kwargs['basetime']		
		if len(args) and 'text' not in kwargs:
			kwargs['text'] = args[0]
		skipmd5 = False
		if 'skipmd5' in kwargs and kwargs['skipmd5']:
			skipmd5 = True
		invalid = set(kwargs.keys()).difference(validargs)		
		if invalid:
			for arg in invalid:
				del kwargs[arg]
		if not self.title:
			self.setPageInfo()	
		if not 'section' in kwargs and self.section is not False:
			kwargs['section'] = self.section
		if not 'text' in kwargs and not 'prependtext' in kwargs and not 'appendtext' in kwargs:
			raise EditError("No text specified")
		if 'prependtext' in kwargs and 'section' in kwargs:
			raise EditError("Bad param combination")
		if 'createonly' in kwargs and 'nocreate' in kwargs:
			raise EditError("Bad param combination")
		token = self.getToken('edit')
		if 'text' in kwargs:
			hashtext = kwargs['text']
		elif 'prependtext' in kwargs and 'appendtext' in kwargs:
			hashtext = kwargs['prependtext']+kwargs['appendtext']
		elif 'prependtext' in kwargs:
			hashtext = kwargs['prependtext']
		else:
			hashtext = kwargs['appendtext']
		params = {
			'action': 'edit',
			'title':self.title,
			'token':token,
		}
		if not skipmd5:
			params['md5'] = md5(hashtext).hexdigest()
		params.update(kwargs)
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'edit' in result and result['edit']['result'] == 'Success':
			self.wikitext = ''
			self.links = []
			self.templates = []
			self.exists = True
		return result
		
	def move(self, mvto, reason=False, movetalk=False, noredirect=False, watch=False, unwatch=False):
		"""Move the page
		
		Params are the same as the API:
		mvto - page title to move to, the only required param
		reason - summary for the log
		movetalk - move the corresponding talk page
		noredirect - don't create a redirect at the previous title
		watch - add the page to your watchlist
		unwatch - remove the page from your watchlist
		
		"""
		if not self.title and self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		token = self.getToken('move')
		params = {
			'action': 'move',
			'to':mvto,
			'token':token,
		}
		if self.pageid:
			params['fromid'] = self.pageid
		else:
			params['from'] = self.title
		if reason:
			params['reason'] = reason.encode('utf-8')
		if movetalk:
			params['movetalk'] = '1'
		if noredirect:
			params['noredirect'] = '1'
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'move' in result:
			self.title = result['move']['to']
			self.namespace = namespaceDetect(self.title, self.site)
			if self.namespace is not 0:
				self.unprefixedtitle = self.title.split(':', 1)[1]
			else:
				self.unprefixedtitle = self.title			
			if not isinstance(self.title, unicode):
				self.title = unicode(self.title, 'utf-8')
				self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')	
			else:
				self.urltitle = urllib.quote(self.title.encode('utf-8')).replace('%20', '_').replace('%2F', '/')
		return result

	def protect(self, restrictions={}, expirations={}, reason=False, cascade=False):
		"""Protect a page
		
		Restrictions and expirations are dictionaries of
		protection level/expiry settings, e.g., {'edit':'sysop'} and
		{'move':'3 days'}. expirations can also be a string to set 
		all levels to the same expiration
		
		reason - summary for log
		cascade - apply protection to all pages transcluded on the page
		
		"""
		if not self.title:
			self.setPageInfo()
		if not restrictions:
			raise ProtectError("No protection levels given")
		if len(expirations) > len(restrictions):
			raise ProtectError("More expirations than restrictions given")
		token = self.getToken('protect')
		protections = ''
		expiry = ''
		if isinstance(expirations, str):
			expiry = expirations
		for type in restrictions:
			if protections:
				protections+="|"
			protections+= type+"="+restrictions[type]
			if isinstance(expirations, dict) and type in expirations:
				if expiry:
					expiry+="|"
				expiry+=expirations[type]
			elif isinstance(expirations, dict):
				if expiry:
					expiry+="|"
				expiry+='indefinite'
		params = {'action':'protect',
			'title':self.title,
			'token':token,
			'protections':protections
		}
		if expiry:
			params['expiry'] = expiry
		if reason:
			params['reason'] = reason
		if cascade:
			params['cascade'] = ''
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'protect' in result:
			self.protection = {}
		return result
	
	def delete(self, reason=False, watch=False, unwatch=False):
		"""Delete the page
		
		reason - summary for log
		watch - add the page to your watchlist
		unwatch - remove the page from your watchlist
		
		"""
		if not self.title and self.pageid == 0:
			self.setPageInfo()
		if not self.exists:
			raise NoPage
		token = self.getToken('delete')
		params = {
			'action': 'delete',
			'token':token,
		}
		if self.pageid:
			params['pageid'] = self.pageid
		else:
			params['title'] = self.title
		if reason:
			params['reason'] = reason.encode('utf-8')
		if watch:
			params['watch'] = '1'
		if unwatch:
			params['unwatch'] = '1'
		req = api.APIRequest(self.site, params, write=True)
		result = req.query()
		if 'delete' in result:
			self.pageid = 0
			self.exists = False
			self.wikitext = ''
			self.templates = ''
			self.links = ''
			self.protection = {}
			self.section = False			
		return result
	
	def getToken(self, type):
		"""Get a token for everything except rollbacks
		
		type (string) - edit, delete, protect, move, block, unblock, email
		Currently all the tokens are interchangeable, but this may change in the future
		
		"""			
		if self.pageid == 0 and not self.title:
			self.setPageInfo()
		if not self.exists and type != 'edit':
			raise NoPage
		params = {
			'action':'query',
			'prop':'info',
			'intoken':type,
		}
		if self.exists and self.pageid:
			params['pageids'] = self.pageid
		else:
			params['titles'] = self.title
		req = api.APIRequest(self.site, params)
		response = req.query()
		if self.pageid == 0:
			self.pageid = response['query']['pages'].keys()[0]
		token = response['query']['pages'][str(self.pageid)][type+'token']
		return token
	
	def __str__(self):
		if self.title:
			title = self.title
		else:
			title = 'pageid: '+self.pageid
		return self.__class__.__name__ +' '+repr(title) + " from " + repr(self.site.domain)
	
	def __repr__(self):
		if self.title:
			title = self.title
		else:
			title = 'pageid: '+self.pageid
		return "<"+self.__module__+'.'+self.__class__.__name__+" "+repr(title)+" using "+repr(self.site.apibase)+">"
	
	def __eq__(self, other):
		if not isinstance(other, Page):
			return False
		if self.title:			
			if self.title == other.title and self.site == other.site:
				return True
		else:
			if self.pageid == other.pageid and self.site == other.site:
				return True
		return False
		
	def __ne__(self, other):
		if not isinstance(other, Page):
			return True
		if self.title:
			if self.title == other.title and self.site == other.site:
				return False
		else:
			if self.pageid == other.pageid and self.site == other.site:
				return False
		return True
