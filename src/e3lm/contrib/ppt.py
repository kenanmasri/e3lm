"""
Author: Kenan Masri

`PptPlugin` is an E3lm interpreter plugin used to generate a slideshow (Powerpoint) file from a specific 3lm file using a specific criteria.
"""
import sys
from copy import deepcopy
from pptx import Presentation
from e3lm.helpers.printers import cprint
from e3lm.lang.interpreters import E3lmPlugin
from e3lm.lang import ast


class PptPlugin(E3lmPlugin): # TODO Write actual PptPlugin
    """An E3lm interpreter plugin used to generate a slideshow (Powerpoint) file from a specific 3lm file using a specific criteria."""

    def __init__(self, *args, **kwargs):
        self.options = kwargs

    def interpret(self, input, source=None):
        return self.visit(input)

    def v_Program(self, obj, *args, **kwargs):
        for i, b in enumerate(obj.blocks):
            obj.blocks[i] = b = self.visit(b)
        return obj

    def v_Block(self, obj, *args, **kwargs):
        for i, b in enumerate(obj.children):
            obj.children[i] = b = self.visit(b)
        return obj
