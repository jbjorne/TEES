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

import urllib2
import re
import time
import sys
from urllib import quote_plus, _is_unicode
try:
	from poster.encode import multipart_encode
	canupload = True
except:
	canupload = False

try:
	import json
except:
	import simplejson as json
try:
	import gzip
	import StringIO
except:
	gzip = False

class APIError(Exception):
	"""Base class for errors"""

class APIDisabled(APIError):
	"""API not enabled"""
	
class APIRequest:
	"""A request to the site's API"""
	def __init__(self, wiki, data, write=False, multipart=False):
		"""	
		wiki - A Wiki object
		data - API parameters in the form of a dict
		write - set to True if doing a write query, so it won't try again on error
		multipart - use multipart data transfer, required for file uploads,
		requires the poster package
		
		maxlag is set by default to 5 but can be changed
		format is always set to json
		"""
		if not canupload and multipart:
			raise APIError("The poster module is required for multipart support")
		self.sleep = 5
		self.data = data.copy()
		self.data['format'] = "json"
		self.iswrite = write
		if not 'maxlag' in self.data and not wiki.maxlag < 0:
			self.data['maxlag'] = wiki.maxlag
		self.multipart = multipart
		if self.multipart:
			(datagen, self.headers) = multipart_encode(self.data)
			self.encodeddata = ''
			for singledata in datagen:
				self.encodeddata = self.encodeddata + singledata
		else:
			self.encodeddata = urlencode(self.data, 1)
			self.headers = {
				"Content-Type": "application/x-www-form-urlencoded",
				"Content-Length": len(self.encodeddata)
			}
		self.headers["User-agent"] = wiki.useragent,
		if gzip:
			self.headers['Accept-Encoding'] = 'gzip'
		self.wiki = wiki
		self.response = False
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(wiki.cookies))
		self.request = urllib2.Request(self.wiki.apibase, self.encodeddata, self.headers)
		
	def setMultipart(self, multipart=True):
		"""Enable multipart data transfer, required for file uploads."""
		if not canupload and multipart:
			raise APIError("The poster package is required for multipart support")
		self.multipart = multipart
		if multipart:
			(datagen, headers) = multipart_encode(self.data)
			self.headers.pop('Content-Length')
			self.headers.pop('Content-Type')
			self.headers.update(headers)
			self.encodeddata = ''
			for singledata in datagen:
				self.encodeddata = self.encodeddata + singledata
		else:
			self.encodeddata = urlencode(self.data, 1)
			self.headers['Content-Length'] = len(self.encodeddata)
			self.headers['Content-Type'] = "application/x-www-form-urlencoded"

	def changeParam(self, param, value):
		"""Change or add a parameter after making the request object
		
		Simply changing self.data won't work as it needs to update other things.

		value can either be a normal string value, or a file-like object,
		which will be uploaded, if setMultipart was called previously.
		
		"""
		if param == 'format':
			raise APIError('You can not change the result format')
		self.data[param] = value
		if self.multipart:
			(datagen, headers) = multipart_encode(self.data)
			self.headers.pop('Content-Length')
			self.headers.pop('Content-Type')
			self.headers.update(headers)
			self.encodeddata = ''
			for singledata in datagen:
				self.encodeddata = self.encodeddata + singledata
		else:
			self.encodeddata = urlencode(self.data, 1)
			self.headers['Content-Length'] = len(self.encodeddata)
			self.headers['Content-Type'] = "application/x-www-form-urlencoded"
		self.request = urllib2.Request(self.wiki.apibase, self.encodeddata, self.headers)
	
	def query(self, querycontinue=True):
		"""Actually do the query here and return usable stuff
		
		querycontinue - look for query-continue in the results and continue querying
		until there is no more data to retrieve
		
		"""
		data = False
		while not data:
			rawdata = self.__getRaw()
			data = self.__parseJSON(rawdata)				
		#Certain errors should probably be handled here...
		if 'error' in data:
			raise APIError(data['error']['code'], data['error']['info'])
		if 'query-continue' in data and querycontinue:
			data = self.__longQuery(data)
		return data
	
	def __longQuery(self, initialdata):
		"""For queries that require multiple requests"""
		self._continues = set()
		self._generator = ''
		total = initialdata
		res = initialdata
		params = self.data
		numkeys = len(res['query-continue'].keys())
		while numkeys > 0:
			key1 = ''
			key2 = ''
			possiblecontinues = res['query-continue'].keys()
			if len(possiblecontinues) == 1:
				key1 = possiblecontinues[0]
				keylist = res['query-continue'][key1].keys()
				if len(keylist) == 1:
					key2 = keylist[0]
				else:
					for key in keylist:
						if len(key) < 11:
							key2 = key
							break
					else:
						key2 = keylist[0]
			else:
				for posskey in possiblecontinues:
					keylist = res['query-continue'][posskey].keys()
					for key in keylist:
						if len(key) < 11:
							key1 = posskey
							key2 = key
							break
					if key1:
						break
				else:
					key1 = possiblecontinues[0]
					key2 = res['query-continue'][key1].keys()[0]
			if isinstance(res['query-continue'][key1][key2], int):
				cont = res['query-continue'][key1][key2]
			else:
				cont = res['query-continue'][key1][key2].encode('utf-8')
			if len(key2) >= 11 and key2.startswith('g'):
				self._generator = key2
				for ckey in self._continues:
					params.pop(ckey, None)		
			else:
				self._continues.add(key2)
			params[key2] = cont
			req = APIRequest(self.wiki, params)
			res = req.query(False)
			for type in possiblecontinues:
				total = resultCombine(type, total, res)
			if 'query-continue' in res:
				numkeys = len(res['query-continue'].keys())
			else:
				numkeys = 0
		return total

	def __getRaw(self):
		data = False
		while not data:
			try:
				if self.sleep >= self.wiki.maxwaittime or self.iswrite:
					catcherror = None
				else:
					catcherror = Exception
				data = self.opener.open(self.request)
				self.response = data.info()
				if gzip:
					encoding = self.response.get('Content-encoding')
					if encoding in ('gzip', 'x-gzip'):
						data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(data.read()))
			except catcherror, exc:
				errname = sys.exc_info()[0].__name__
				errinfo = exc
				print("%s: %s trying request again in %d seconds" % (errname, errinfo, self.sleep))
				time.sleep(self.sleep+0.5)
				self.sleep+=5
		return data

	def __parseJSON(self, data):
		maxlag = True
		while maxlag:
			try:
				maxlag = False
				parsed = json.loads(data.read())
				content = None
				if isinstance(parsed, dict):
					content = APIResult(parsed)
					content.response = self.response.items()
				elif isinstance(parsed, list):
					content = APIListResult(parsed)
					content.response = self.response.items()
				else:
					content = parsed
				if 'error' in content:
					error = content['error']['code']
					if error == "maxlag":
						lagtime = int(re.search("(\d+) seconds", content['error']['info']).group(1))
						if lagtime > self.wiki.maxwaittime:
							lagtime = self.wiki.maxwaittime
						print("Server lag, sleeping for "+str(lagtime)+" seconds")
						maxlag = True
						time.sleep(int(lagtime)+0.5)
						return False
			except: # Something's wrong with the data...
				data.seek(0)
				if "MediaWiki API is not enabled for this site. Add the following line to your LocalSettings.php<pre><b>$wgEnableAPI=true;</b></pre>" in data.read():
					raise APIDisabled("The API is not enabled on this site")
				print "Invalid JSON, trying request again"
				# FIXME: Would be nice if this didn't just go forever if its never going to work
				return False
		return content
		
class APIResult(dict):
	response = []
	
class APIListResult(list):
	response = []
		
def resultCombine(type, old, new):
	"""Experimental-ish result-combiner thing
	
	If the result isn't something from action=query,
	this will just explode, but that shouldn't happen hopefully?
	
	"""
	ret = old
	if type in new['query']: # Basic list, easy
		ret['query'][type].extend(new['query'][type])
	else: # Else its some sort of prop=thing and/or a generator query
		for key in new['query']['pages'].keys(): # Go through each page
			if not key in old['query']['pages']: # if it only exists in the new one
				ret['query']['pages'][key] = new['query']['pages'][key] # add it to the list
			else:
				if not type in new['query']['pages'][key]:
					continue
				elif type in new['query']['pages'][key] and not type in ret['query']['pages'][key]: # if only the new one does, just add it to the return
					ret['query']['pages'][key][type] = new['query']['pages'][key][type]
					continue					
				else: # Need to check for possible duplicates for some, this is faster than just iterating over new and checking for dups in ret
					retset = set([tuple(entry.items()) for entry in ret['query']['pages'][key][type]])
					newset = set([tuple(entry.items()) for entry in new['query']['pages'][key][type]])
					retset.update(newset)
					ret['query']['pages'][key][type] = [dict(entry) for entry in retset]
	return ret
		
def urlencode(query,doseq=0):
    """
	Hack of urllib's urlencode function, which can handle
	utf-8, but for unknown reasons, chooses not to by 
	trying to encode everything as ascii
    """
    if hasattr(query,"items"):
        # mapping objects
        query = query.items()
    else:
        # it's a bother at times that strings and string-like objects are
        # sequences...
        try:
            # non-sequence items should not work with len()
            # non-empty strings will fail this
            if len(query) and not isinstance(query[0], tuple):
                raise TypeError
            # zero-length sequences of all types will get here and succeed,
            # but that's a minor nit - since the original implementation
            # allowed empty dicts that type of behavior probably should be
            # preserved for consistency
        except TypeError:
            ty,va,tb = sys.exc_info()
            raise TypeError, "not a valid non-string sequence or mapping object", tb

    l = []
    if not doseq:
        # preserve old behavior
        for k, v in query:
            k = quote_plus(str(k))
            v = quote_plus(str(v))
            l.append(k + '=' + v)
    else:
        for k, v in query:
            k = quote_plus(str(k))
            if isinstance(v, str):
                v = quote_plus(v)
                l.append(k + '=' + v)
            elif _is_unicode(v):
                # is there a reasonable way to convert to ASCII?
                # encode generates a string, but "replace" or "ignore"
                # lose information and "strict" can raise UnicodeError
                v = quote_plus(v.encode("utf8","replace"))
                l.append(k + '=' + v)
            else:
                try:
                    # is this a sufficient test for sequence-ness?
                    x = len(v)
                except TypeError:
                    # not a sequence
                    v = quote_plus(str(v))
                    l.append(k + '=' + v)
                else:
                    # loop over the sequence
                    for elt in v:
                        l.append(k + '=' + quote_plus(str(elt)))
    return '&'.join(l)

