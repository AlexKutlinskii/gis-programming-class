# -*- coding: utf-8 -*-
def classFactory(iface):  # noqa: N802
    """Load Kutlinskiy plugin class from file kutlinskiy.py"""
    from .kutlinskiy import KutlinskiyPlugin
    return KutlinskiyPlugin(iface)
