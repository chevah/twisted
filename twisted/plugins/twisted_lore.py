
from zope.interface import implementer

from twisted.python.compat import _PY3
from twisted.plugin import IPlugin

if _PY3:
    # Lore is deprecated and will not be ported to Python 3.
    pass
else:
    from twisted.lore.scripts.lore import IProcessor

    @implementer(IPlugin, IProcessor)
    class _LorePlugin(object):

        def __init__(self, name, moduleName, description):
            self.name = name
            self.moduleName = moduleName
            self.description = description

    DefaultProcessor = _LorePlugin(
        "lore",
        "twisted.lore.default",
        "Lore format")

    MathProcessor = _LorePlugin(
        "mlore",
        "twisted.lore.lmath",
        "Lore format with LaTeX formula")

    SlideProcessor = _LorePlugin(
        "lore-slides",
        "twisted.lore.slides",
        "Lore for slides")

    ManProcessor = _LorePlugin(
        "man",
        "twisted.lore.man2lore",
        "UNIX Man pages")

    NevowProcessor = _LorePlugin(
        "nevow",
        "twisted.lore.nevowlore",
        "Nevow for Lore")
