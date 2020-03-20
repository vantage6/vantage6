# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


class JSDict(object):
    """JavaScript-like access to JSON data."""
    def __init__(self, js_obj):
        self._js_obj = js_obj
    
    def __getattr__(self, key):
        value = self._js_obj[key]
        
        if type(value) in [list, dict]:
            return JSDict(value)
        
        return value
    
    def __contains__(self, item):
        return self._js_obj.__contains__(item)
    
    def __getitem__(self, idx):
        return self.__getattr__(idx)
    
    def __setitem__(self, idx, value):
        self._js_obj[idx] = value
        
    def append(self, item):
        self._js_obj.append(item)

    def get(self, key, default=None):
        return self._js_obj.get(key, default)
    
    def __repr__(self):
        return pprint.pformat(self._js_obj)
    
