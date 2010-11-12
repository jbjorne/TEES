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

import api
import page
import category
import wikifile
import math

def listFromQuery(site, queryresult):
	"""Generate a list of pages from an API query result
	
	queryresult is the list of pages from a list or generator query
	e.g. - for a list=categorymembers query, use result['query']['categorymembers']
	for a generator query, use result['query']['pages']
	
	"""
	ret = []
	if isinstance(queryresult, list):
		for item in queryresult:
			pageid = False
			if 'pageid' in item:
				pageid = item['pageid']
			if item['ns'] == 14:
				item = category.Category(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			if item['ns'] == 6:
				item = wikifile.File(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			else:
				item = page.Page(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			ret.append(item)
	else:
		for key in queryresult.keys():
			item = queryresult[key]
			pageid = False
			if 'pageid' in item:
				pageid = item['pageid']
			if item['ns'] == 14:
				item = category.Category(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			if item['ns'] == 6:
				item = wikifile.File(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			else:
				item = page.Page(site, title=item['title'], check=False, followRedir=False, pageid=pageid)
			ret.append(item)
	return ret

def listFromTitles(site, titles, check=True, followRedir=False):
	"""Create a list of page objects from a list of titles
	
	check and followRedir have the same meaning as in page.Page
	
	"""
	ret = []
	if not check:
		for title in titles:
			title = page.Page(site, title=title, check=False)
			ret.append(title)
	else:
		querylist = []
		limit = int(site.limit)
		if len(titles) > limit/10:
			iters = int(math.ceil(float(len(titles)) / (limit/10)))
			for x in range(0,iters):
				lower = x*limit/10
				upper = (x+1)*limit/10
				querylist.append(titles[lower:upper])
		else:
			querylist.append(titles)
		response = False
		for item in querylist:
			tlist = '|'.join(item)
			if not isinstance(tlist, unicode):
				tlist = unicode(tlist, 'utf8')
			params = {'action':'query',
				'titles':tlist,
			}
			if followRedir:
				params['redirects'] = ''
			req = api.APIRequest(site, params)
			res = req.query(False)
			if not response:
				response = res
			else:
				# This breaks on non-existent titles, the api gives them negative numbers
				# resultCombine doesn't account for this and ignores or overwrites the 
				# duplicate pageids
				response = api.resultCombine('', response, res)
		for key in response['query']['pages'].keys():
			res = response['query']['pages'][key]
			item = makePage(key, res, site)
			ret.append(item)
	return ret

def listFromPageids(site, pageids, check=True, followRedir=False):			
	"""Create a list of page objects from a list of pageids
	
	check and followRedir have the same meaning as in page.Page
	
	"""
	ret = []
	if not check:
		for id in pageids:
			title = page.Page(site, pageid=id, check=False)
			ret.append(title)
	else:
		querylist = []
		limit = int(site.limit)
		if len(pageids) > limit/10:
			iters = int(math.ceil(float(len(pageids)) / (limit/10)))
			for x in range(0,iters):
				lower = x*limit/10
				upper = (x+1)*limit/10
				querylist.append(pageids[lower:upper])
		else:
			querylist.append(pageids)
		response = False
		for item in querylist:
			ids = [str(id) for id in item]
			idlist = '|'.join(ids)
			params = {'action':'query',
				'pageids':idlist,
			}
			if followRedir:
				params['redirects'] = ''
			req = api.APIRequest(site, params)
			res = req.query()
			if not response:
				response = res
			else:
				response = api.resultCombine('', response, res)
		for key in response['query']['pages'].keys():
			res = response['query']['pages'][key]
			item = makePage(key, res, site)
			ret.append(item)
	return ret
	
def makePage(key, result, site):
	title=False
	if 'title' in result:
		title = result['title']
	if 'ns' in result and result['ns'] == 14:
		item = category.Category(site, title=title, check=False, followRedir=False, pageid=key)
	elif 'ns' in result and result['ns'] == 6:
		item = wikifile.File(site, title=title, check=False, followRedir=False, pageid=key)
	else:
		item = page.Page(site, title=title, check=False, followRedir=False, pageid=key)
	if 'missing' in result:
		item.exists = False
	if 'invalid' in result:
		item = False
	if 'ns' in result:
		item.setNamespace(int(result['ns']))
	return item
