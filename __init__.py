# -*- coding: utf-8 -*-
def classFactory(iface):
    from .plugin import ReTKY2JGDPlugin
    return ReTKY2JGDPlugin(iface)
