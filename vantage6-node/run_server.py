#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pytaskmanager import server

if __name__ == '__main__':
    server.init()
    server.run(debug=True, host='0.0.0.0', port=5000)