"""
Author: Kenan Masri

`UnitsPlugin` is an E3lm interpreter plugin used to pick Attrs that end with
"_unit", create a `Unit` object and relate it to the main attribute without the
ending.

Eventually matching Attrs will have a `Unit` attached thereto.
"""
import sys
from copy import deepcopy
from e3lm.helpers.printers import cprint
from e3lm.lang.interpreters import E3lmPlugin
from e3lm.lang import ast


class Unit():
    """Base unit."""

    def __init__(self, id="unit", name="units", **kwargs):
        self.id = id
        self.name = name
        self.converts_to = {}
        if "converts_to" in kwargs.keys():
            self.converts_to = kwargs["converts_to"]
        if type(self.converts_to) in (set, list, tuple):
            sett = self.converts_to
            self.converts_to = {}

            for s in sett[1].converts_to:
                val = sett[1].converts_to[s]
                self.converts_to[s] = sett[0]*val

    def convert(self, target, amount):
        if type(target) != Unit:
            for ustr in [g for g in dir(sys.modules[__name__])
                         if not g.startswith('_')]:
                u = getattr(sys.modules[__name__], ustr)
                if type(u) == Unit:
                    if u.id == target:
                        target = u
        if type(target) == Unit:
            return amount * self.converts_to[target.id]
        else:
            raise ValueError("Cannot convert from {} to {}".format(
                self.id, target))

    def __str__(self):
        return "Unit("+self.id+")"


inch = Unit("in", "inches", converts_to={
    "px": 96,
    "pt": 72,
    "pc": 6,
    "cm": 2.54,
    "mm": 25.4,
    "m": 0.0254,
    "in": 1.0,
})
cm = Unit("cm", "centimeters", converts_to={
    "px": 37.79527559055118,
    "pt": 28.346456692913385,
    "pc": 2.3622047244094486,
    "mm": 10.0,
    "cm": 1.0,
    "m": 0.01,
    "in": 0.39370078740157477,
})
mm = Unit("mm", "millimeters", converts_to=(0.1, cm))
m = Unit("m", "meters", converts_to=(100, cm))
km = Unit("km", "kilometers", converts_to=(1000, m))
px = Unit("px", "pixels", converts_to=(1/96, inch))
pt = Unit("pt", "points", converts_to=(1/72, inch))
pc = Unit("pc", "picas", converts_to=(12, pt))


class UnitsPlugin(E3lmPlugin):
    """An E3lm interpreter plugin used to pick Attrs that end with "_unit",
    create a `Unit` object and relate it to the main attribute without the
    ending."""

    def __init__(self, *args, **kwargs):
        self.options = kwargs
        self.units = {
            "inch": inch,
            "cm": cm,
            "mm": mm,
            "m": m,
            "km": km,
            "px": px,
            "pt": pt,
            "pc": pc,
        }

    def interpret(self, input, source=None):
        return self.visit(input)

    def v_Program(self, obj, *args, **kwargs):
        for i, b in enumerate(obj.blocks):
            obj.blocks[i] = b = self.visit(b)
        return obj

    def v_Block(self, obj, *args, **kwargs):
        for i, b in enumerate(obj.children):
            obj.children[i] = b = self.visit(b)

        nattrs = [a.name for i, a in obj._attrs.items()]
        vattrs = []
        for i, a in obj._attrs.items():
            if a.name.endswith("_unit"):
                if a.name[:-5] in nattrs:
                    vattrs.append((a, a.name[:-5]))

        for s in vattrs:
            obj._attrs[s[0]] = self.v_Attr(s[0], obj._attrs[s[1]])
        return obj

    def v_Attr(self, obj, main_attr):
        main_attr.unit = deepcopy(self.units[obj.eval])
        main_attr.convert = lambda u: main_attr.unit.convert(u, main_attr.eval)
        return obj
