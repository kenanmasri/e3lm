"""
Author: Kenan Masri

"""
import sys
import functools
from jinja2 import Template
from e3lm.lang import ast
from e3lm.lang.data import basic_dt
from e3lm.helpers.printers import cprint

stuck_counter = 0


class InterpreterError(BaseException):
    pass


def get_attr(obj, attr):
    """Return `attr` of `obj` by searching its `children`, `attrs` and actual
    attributes in order."""
    search = obj
    if isinstance(obj, ast.AST):
        if hasattr(obj, "eval") and obj.eval != None:
            search = obj.eval

    sattr = attr
    if isinstance(attr, ast.AST):
        if hasattr(attr, "eval") and attr.eval != None:
            sattr = attr.eval

    if isinstance(search, ast.AST):
        if type(search) == ast.Identifier:
            pass
        if type(search) == ast.Program:
            flat_blocks = search.flat_blocks
            for fb in flat_blocks:
                if sattr == fb.name:
                    return fb

    if isinstance(sattr, ast.AST):
        if type(sattr) == ast.Block:
            raise AttributeError

    if type(search) in (list, dict, tuple, set):
        try:
            return search[sattr]
        except (KeyError, ValueError):
            return search[int(sattr)]

    if hasattr(search, "children"):
        names = [n.name for n in search.children]
        if sattr in names:
            return search.children[names.index(sattr)]

    if hasattr(search, "_attrs"):
        if sattr in search._attrs.keys():
            return search._attrs[sattr]

    if hasattr(search, sattr):
        return getattr(search, sattr)

    # Return empty body since it was not found.
    if type(search) == ast.Block and attr == "body":
        return ""

    raise AttributeError("'{}' object has no attribute '{}'.".format(
        search, attr
    ))


def dot_get(obj, attr, *args, **kwargs):
    """Get `obj` nested `attr` in dotted syntax.

    Available Keyword Arguments:
        `eval` whether return evaluation or AST.

    Examples:
        dot_get(my_program, "dummy_1.attr2")
        dot_get(my_program, "blocks.0.dummy_2")
    """
    if "eval" in kwargs.keys():
        _eval = kwargs["eval"]
    else:
        _eval = False

    def _getattr(obj, attr):
        if hasattr(obj, "attrs"):
            if attr in obj.attrs.keys():
                return obj.attrs[attr] if _eval else obj._attrs[attr]
        try:
            if type(obj) in (list, dict, tuple, set):
                try:
                    return obj[int(attr)]
                except (KeyError, ValueError):
                    return obj[attr]
        except ValueError:
            raise AttributeError(f"{attr} was not found in {obj}")
        try:
            n = get_attr(obj, attr)
        except AttributeError:
            n = getattr(obj, attr, *args)
        return n

    dot = functools.reduce(_getattr, [obj] + attr.split('.'))
    return dot


class NodeVisitor:
    """Base node visitor."""

    def __init__(self):
        self._idgen = 0

    def id(self):
        self._idgen += 1
        return self._idgen - 1

    def generic_visit(self, v):
        return v

    def visit(self, node):
        """"""
        if not hasattr(node, "_id") and type(node) not in ast.basic_dt:
            node._id = self.id()

        method = 'visit_{}'.format(type(node).__name__)
        result = node
        visitor = getattr(self, method, self.generic_visit)
        if visitor == self.generic_visit:
            raise NotImplementedError("No {} method.".format(method))
        else:
            result = visitor(result)
        return result


class Functions:
    """Base class for functions."""
    @staticmethod
    def type_method(interpreter,
                    inp=None, name="", args=[], **kwargs):
        return getattr(inp, name)(*args)

    @staticmethod
    def prev(interpreter, *args, **kwargs):
        klass = None
        if len(args) > 0:
            klass = args[0]
        return interpreter.get_prev(klass, None)

    @staticmethod
    def next(interpreter, *args, **kwargs):
        klass = None
        if len(args) > 0:
            klass = args[0]
        return interpreter.get_next(klass, None)


class E3lmInterpreter(NodeVisitor):
    """Main E3lm Interpreter."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        if "parser_kwargs" in kwargs.keys():
            self.parser_kwargs = kwargs["parser_kwargs"]
        else:
            self.parser_kwargs = {}
        if "parser" in kwargs.keys():
            self.parser = kwargs["parser"]
        else:
            self.parser = None

    def interpret(self, input, source=None):
        if type(input) == str:
            if self.parser:
                tree = self.parser.parse(input, source, **self.parser_kwargs)
            else:
                raise Exception("Cannot interpret text without a parser.")
        else:
            tree = input
        if tree == None:
            return None
        self.program = tree
        # Here we visit all blocks and subblocks to append to the flat_blocks
        # list for use later.
        self.num_visit = 1
        self.lazy_attrs = []
        self.program = self.visit(self.program)
        self.program.flat_blocks = self.flat_blocks
        while len(self.lazy_attrs) > 0:
            self.num_visit += 1
            self.program = self.visit(self.program)
        return self.program

    def id(self):
        """Generate an ID."""
        self._idgen += 1
        return self._idgen - 1

    def visit(self, node, evaluate=False):
        if node == None:
            return None
        if not hasattr(node, "_id") and type(node) not in ast.basic_dt:
            node._id = self.id()

        # Check if the object is provided as plugin.
        is_plugin = False
        if hasattr(self, "is_plugin"):
            is_plugin = self.is_plugin

        method = 'v_{}'.format(type(node).__name__)

        result = node
        visitor = getattr(self, method, self.generic_visit)
        if visitor == self.generic_visit:
            raise NotImplementedError("No {} method.".format(method))
        else:
            result = visitor(result, evaluate=evaluate)
        return result

    def get_next(self, klass=None, obj=None):
        obj = obj or self.current_block

        a = self.filter_flat(klass=klass)
        if obj not in a:
            n = 0
        else:
            n = a.index(obj) + 1
        if klass:
            for i in range(len(a)):
                try:
                    if a[n+i].type == klass:
                        return a[n+i]
                except IndexError:
                    break
        else:
            if n >= len(a):
                return None
            try:
                return a[n]
            except IndexError:
                raise RecursionError("Cannot get next({}) of object {}."
                                     .format(str(klass), str(obj)))

    def get_prev(self, klass=None, obj=None):
        obj = obj or self.current_block
        a = self.filter_flat(klass=klass)
        if obj not in a:
            n = 0
        else:
            n = a.index(obj) - 1
        if klass:
            for i in range(len(a)):
                if n-i < 0:
                    return None
                try:
                    if a[n-i].type == klass:
                        return a[n-i]
                except IndexError:
                    break
        else:
            if n < 0:
                return None
            try:
                return a[n]
            except IndexError:
                raise RecursionError("Cannot get prev({}) of object {}."
                                     .format(str(klass), str(obj)))

    def filter_flat(self, klass=None):
        """Get `flat_blocks` filtered by `klass`."""
        store = self.flat_blocks
        if klass:
            return [a for a in store if a.type == klass]
        else:
            return store

    def abs_eval(self, obj, **kwargs):
        """Return the absolute `eval` of `obj`"""
        _types = (ast.Attr, ast.Identifier)
        cblock = self.current_block
        while type(obj) in _types:
            if hasattr(obj, "eval"):
                if type(obj) == ast.Attr:
                    self.current_block = obj.parent
                    if obj not in self.current_attr._eval:
                        self.current_attr._eval.append(obj)
                    obj = self.visit(obj, evaluate=2)
                    if type(obj) in ast.basic_dt:
                        break
                if type(obj) == ast.Block:
                    return obj
                if obj.eval == None or obj.eval == obj:
                    if obj not in self.current_attr._eval:
                        self.current_attr._eval.append(obj)
                    obj = self.visit(obj, evaluate=2)
                    if type(obj) in ast.basic_dt:
                        break
                obj = obj.eval
            else:
                obj = self.visit(obj, evaluate=True)
        self.current_block = cblock
        if type(obj) not in _types:
            obj = self.visit(obj, evaluate=True)
        if obj not in self.current_attr._eval:
            self.current_attr._eval.append(obj)
        return obj

    def v_Program(self, obj, *args, **kwargs):
        self.current_block = None
        if not hasattr(self, "flat_blocks"):
            self.flat_blocks = []
        if not hasattr(self, "_nav"):
            self._nav = []

        def add_to_nav(slf, b):
            if b not in slf._nav:
                slf._nav.append(b)
                if len(b.children) > 0:
                    for bb in b.children:
                        add_to_nav(slf, bb)

        for i, b in enumerate(obj.blocks):
            add_to_nav(self, b)

        for i, b in enumerate(obj.blocks):
            obj.blocks[i] = b = self.visit(b, evaluate=True)

        return obj

    def v_Type(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        if evaluate:
            obj.eval = obj.value
            return obj.eval
        return obj

    def v_Block(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()
        if not hasattr(obj, "parent"):
            obj.parent = self.current_block or self.program

        if not obj in self._nav:
            self._nav.append(obj)

        if obj not in self.flat_blocks:
            self.flat_blocks.append(obj)

        # Visit children blocks and then attributes.
        for i, b in enumerate(obj.children):
            self.current_block = obj
            obj.children[i] = b = self.visit(b, evaluate=evaluate)

        if not hasattr(obj, "attrs"):
            obj.attrs = {}

        for i, a in obj._attrs.items():
            self.current_block = obj
            self.current_attr = obj._attrs[i]
            try:
                obj._attrs[i] = self.visit(a, evaluate=True)
            except RecursionError:
                continue
            self.current_block = obj
            if evaluate != False:
                self.current_attr = obj._attrs[i]
                obj.attrs[i] = a.eval = self.visit(a, evaluate=2)

        return obj

    def v_Attr(self, obj, *args, **kwargs):
        global stuck_counter  # For stack overflow avoidance
        # --- RETURN BASED ON EVALUATE ---
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_lazy"):
            obj._lazy = 1
        if not hasattr(obj, "_id"):
            obj._id = self.id()
        if not hasattr(obj, "parent"):
            obj.parent = self.current_block
        if not hasattr(obj, "_eval"):
            obj._eval = []

        if obj in self.lazy_attrs and obj._lazy == self.num_visit:
            if self.current_attr not in self.lazy_attrs:
                self.current_attr.lazy = self.num_visit
                self.lazy_attrs.append(self.current_attr)
            return ast.Lazy() if evaluate == 2 else obj

        if obj.name == "body":
            obj = self.v_body(obj, evaluate=False)
            obj.eval = self.v_body(obj, evaluate=True)
            obj._eval.append(obj.eval)
            return obj.eval if evaluate == 2 else obj
        else:
            if len(obj._eval) >= 1 and type(obj._eval[-1]) == ast.Attr:
                if obj.name == obj._eval[-1].name:
                    raise RecursionError
            try:
                obj.value = self.visit(obj.value, evaluate=False)
                _eval = self.visit(obj.value, evaluate=2)
                if _eval not in obj._eval:
                    obj._eval.append(_eval)

                obj.eval = self.abs_eval(_eval)
                if obj in self.lazy_attrs:
                    self.lazy_attrs.remove(obj)

                # Removed recursion limit for 3lm interpreter..
                # Basically a 3lm file won't be that large.

                # stuck_counter += 1
                # if stuck_counter > sys.getrecursionlimit():
                    # print("Stuck at recursion: " + str(stuck_counter) + "\nThe attribute", obj, "is bugged. Please check your 3lm code.")
                    # stuck_counter = 0
                    # exit(1)

                return obj.eval if evaluate == 2 else obj
            except (AttributeError, ValueError) as e:
                if obj not in self.lazy_attrs:
                    obj.lazy = self.num_visit
                    self.lazy_attrs.append(obj)
                return obj

    # TODO better Jinja2 implementation
    def v_body(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if evaluate:
            if not hasattr(obj, "_body_template"):
                val = obj.value
                if isinstance(val, ast.Str):
                    val = str(val.value)
                obj._body_template = Template(val)
            kwargs = self.current_block.attrs
            if isinstance(obj, ast.Attr):
                obj.tokens = []
            kwargs = {**kwargs, "tokens": obj.tokens}
            obj.eval = obj._body_template.render(**kwargs)
            return obj.eval if evaluate else obj
        # return obj
        # obj.eval = obj.value
        return obj.eval if evaluate else obj

    def v_Identifier(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        for i, a in enumerate(obj.children):
            obj.children[i] = a = self.visit(a, evaluate=False)
            if isinstance(obj.children[i], ast.AST):
                if type(obj.children[i]) not in (ast.Block,):
                    obj.children[i].eval = self.visit(a, evaluate=True)

        c = None  # current child
        a = None  # child
        skip = False
        for i, a in enumerate(obj.children):
            if skip:
                skip = False
                continue
            b = obj.children[i+1] if i+1 < len(obj.children) else None
            if b != None:
                _d = False  # Whether done tests.
                # If func, get the argument before and do it as an attribute.
                if type(b) == ast.Func:
                    # Visit arguments:
                    fname = b.value  # e.g. split
                    inp = self.abs_eval(a)
                    ch = [self.abs_eval(_c) for _c in b.children]
                    try:
                        test = Functions.type_method(self,
                                                     inp=inp, name=fname,
                                                     args=ch)
                        _d = True
                    except AttributeError as e:
                        raise e from None
                else:
                    # Try the attribute method.
                    bb = b.eval if hasattr(b, "eval") else b
                    aa = a.eval if hasattr(a, "eval") else a
                    if aa == None:
                        raise AttributeError(f"None does not have {bb}")
                    try:
                        if c == None:
                            _c = self.current_block
                            c = _c
                        else:
                            _c = self.abs_eval(c)
                        test = get_attr(_c, aa)
                        c = test
                        obj.eval = c
                        _d = False  # Do not skip
                    except AttributeError:
                        try:
                            test = get_attr(aa, bb)
                            obj.eval = test
                            c = test
                            _d = True
                        except AttributeError as e:
                            # Try the local/global keyword
                            arr = [(_b.name, _b.type)
                                   for _b in self.flat_blocks]
                            try:
                                ar = [k[0] for k in arr]
                                test = self.flat_blocks[ar.index(aa)]
                                c = test
                                obj.eval = test
                                _d = False
                            except ValueError:
                                try:
                                    ar = [k[1] for k in arr]
                                    test = self.flat_blocks[ar.index(aa)].type
                                    obj.eval = test
                                    _d = False
                                except ValueError:
                                    raise AttributeError(
                                        "keyword '{}' does not exist.".format(
                                            aa
                                        ))
                if _d:
                    obj.eval = test
                    skip = True
            else:
                _d = False
                aa = a.eval if hasattr(a, "eval") else a
                # Try the local/global keyword
                try:
                    if c == None:
                        c = self.current_block
                    test = get_attr(c, aa)
                    c = test
                    obj.eval = c
                    _d = False  # Do not skip
                except AttributeError:
                    arr = [(_b.name, _b.type)
                           for _b in self._nav]
                    try:
                        ar = [k[1] for k in arr]
                        test = self._nav[ar.index(aa)].type
                        obj.eval = test
                        _d = False
                    except ValueError:
                        try:
                            ar = [k[0] for k in arr]
                            test = self._nav[ar.index(aa)]
                            c = test
                            obj.eval = test
                            _d = False
                        except ValueError:
                            # Check if aa does not exist as global block
                            ar = [k.name for k in self._nav]
                            ar2 = [k.type for k in self._nav]
                            if aa not in ar:
                                print(ar)
                                if aa not in ar2:
                                    raise InterpreterError(
                                        f"{c} does not have {aa}."
                                    ) from None
                                else:
                                    test = self._nav[ar.index(aa)].type
                                    obj.eval = test
                                    _d = False
                            else:
                                # Check if aa does not exist on block/attr
                                if type(c) == ast.Attr:
                                    c = c._eval[0]
                                if aa not in c.attrs:
                                    test = self._nav[ar.index(aa)]
                                    obj.eval = test
                                    _d = False
                                else:
                                    raise AttributeError(
                                        "keyword '{}' does not exist.".format(
                                            aa
                                        )) from None

                if _d:
                    obj.eval = test
                    if type(obj.eval) == ast.Attr:
                        obj.target = obj.eval
                        obj.eval = self.visit(obj.eval, evaluate=2)
        if not hasattr(obj, "eval"):
            raise SyntaxError("keyword '" + str(obj.children[0])
                              + "' is unknown.") from None

        return obj.eval if evaluate else obj

    def v_Index(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        obj.eval = self.visit(obj.value, evaluate=True)
        return obj.eval if evaluate else obj

    def v_UnaryOp(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        op = obj.op
        ev = self.visit(obj.value, evaluate=True)
        while (type(ev) not in ast.basic_dt):
            ev = self.abs_eval(ev)

        if op == "+":
            obj.eval = + ev
        elif op == "-":
            obj.eval = - ev
        return obj.eval if evaluate else obj

    def v_BinOp(self, obj, *args, **kwargs):

        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        leval = self.visit(obj.left, evaluate=True)
        reval = self.visit(obj.right, evaluate=True)

        while (type(leval) not in ast.basic_dt) \
                or (type(reval) not in ast.basic_dt):
            leval = self.abs_eval(leval)
            reval = self.abs_eval(reval)

        try:
            if obj.op == "+":
                obj.eval = leval + reval
            elif obj.op == "-":
                obj.eval = leval - reval
            elif obj.op == "*":
                obj.eval = leval * reval
            elif obj.op == "/":
                obj.eval = leval / reval
            elif obj.op == "**":
                obj.eval = leval ** reval
            elif obj.op == "//":
                obj.eval = leval // reval
        except TypeError as e:
            raise TypeError("attr '"
                            + str(self.current_attr.name) + "' in block '"
                            + str(self.current_block) + "' invalid "
                            + str(obj) + ".")
        return obj.eval if evaluate else obj

    def v_Num(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        obj.eval = obj.value
        if obj.type == "NUM_FLOAT":
            obj.eval = float(obj.value)
        elif obj.type == "NUM_OCT":
            obj.eval = int(obj.value, base=8)
        elif obj.type == "NUM_BIN":
            obj.eval = int(obj.value, base=2)
        elif obj.type == "NUM_HEX":
            obj.eval = int(obj.value, base=16)
        elif obj.type == "NUM_IMAG":
            obj.eval = obj.value[0]
        return obj.eval if evaluate else obj

    def v_Str(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        # Convert to a Type if it means a type literal.
        # if obj.value in [b.type for b in self.flat_blocks]:
        #     obj = ast.Type(obj.value)

        obj.eval = self.visit(obj.value, evaluate=True)
        return obj.eval if evaluate else obj

    def v_Bool(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        obj.eval = self.visit(obj.value, evaluate=True)
        return obj.eval if evaluate else obj

    def v_Undefined(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()
        obj.eval = self.visit(obj.value, evaluate=True)
        return obj.eval if evaluate else obj

    def v_obj(self, obj, *args, **kwargs):
        return obj

    def v_dict(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if evaluate:
            return {self.visit(key, evaluate=True): self.visit(val)
                    for key, val in obj.items()}
        else:
            return {self.visit(key, evaluate=False): self.visit(
                val, evaluate=False) for key, val in obj.items()}

    def v_list(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        return [self.visit(val, evaluate=evaluate) for val in obj]

    v_str = v_obj
    v_int = v_obj
    v_float = v_obj
    v_tuple = v_obj
    v_complex = v_obj
    v_bool = v_obj

    def v_Array(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        _ar = []
        for a in obj.children:
            a = self.visit(a, evaluate=True)
            if hasattr(a, "eval"):
                a = a.eval
            _ar.append(a)
        obj.eval = _ar
        return obj.eval if evaluate else obj

    def v_Dict(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        _dict = {}
        for cpl in obj.children:
            cpl.left = self.visit(cpl.left, evaluate=True)
            cpl.right = self.visit(cpl.right, evaluate=True)
            cpl_left = cpl.left.eval \
                if "eval" in dir(cpl.left) else cpl.left
            cpl_right = cpl.right.eval \
                if "eval" in dir(cpl.right) else cpl.right
            _dict[cpl_left] = cpl_right
        obj.eval = _dict
        return obj.eval if evaluate else obj

    def v_Func(self, obj, *args, **kwargs):
        evaluate = kwargs["evaluate"]
        if not hasattr(obj, "_id"):
            obj._id = self.id()

        for i, a in enumerate(obj.children):
            a.eval = self.visit(a, evaluate=True)
            obj.children[i] = a

        fname = self.visit(obj.value, evaluate=True)

        obj.call = getattr(Functions,
                           fname, None)
        if obj.call:
            obj.eval = obj.call(self, *[a.eval for a in obj.children])
        else:
            return obj
        return obj.eval if evaluate else obj


class E3lmPlugin(E3lmInterpreter):
    """Base class for an E3lm interpretation plugin.

    `options` must contain a "key" that indicates what attribute to
    assign to the program.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = kwargs
        self.is_plugin = True

    def interpret(self, input, source=None):
        self.program = input
        new_data = self.visit(self.program)
        if "key" in self.options.keys():
            attr = self.options["key"]
        else:
            raise NotImplementedError("Interpret is not implemented properly.")
        setattr(self.program, attr, new_data)
        return self.program

    def v_Program(self, obj, *args, **kwargs):
        for i, b in enumerate(obj.blocks):
            b = self.visit(b)
        return obj

    def v_Block(self, obj, *args, **kwargs):
        ast = False
        if "ast" in self.options.keys():
            ast = self.options["ast"]

        for i, b in enumerate(obj.children):
            b = self.visit(b)

        for i, b in enumerate(obj.attrs):
            b = self.visit(b)

        return obj
