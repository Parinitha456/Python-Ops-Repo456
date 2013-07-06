import ast
import sys
from functools import partial

from pandas.core.base import StringMixin
from pandas.computation.ops import BinOp, UnaryOp, _reductions, _mathops
from pandas.computation.ops import _cmp_ops_syms, _bool_ops_syms
from pandas.computation.ops import _arith_ops_syms, _unary_ops_syms
from pandas.computation.ops import Term, Constant

class Scope(object):
    __slots__ = 'globals', 'locals'

    def __init__(self, gbls=None, lcls=None, frame_level=1):
        frame = sys._getframe(frame_level)

        try:
            self.globals = gbls or frame.f_globals.copy()
            self.locals = lcls or frame.f_locals.copy()
        finally:
            del frame

class ExprParserError(Exception):
    pass


class ExprVisitor(ast.NodeVisitor):
    """Custom ast walker
    """
    bin_ops = _cmp_ops_syms + _bool_ops_syms + _arith_ops_syms
    bin_op_nodes = ('Gt', 'Lt', 'GtE', 'LtE', 'Eq', 'NotEq', 'BitAnd', 'BitOr',
                    'Add', 'Sub', 'Mult', 'Div', 'Pow', 'FloorDiv', 'Mod')
    bin_op_nodes_map = dict(zip(bin_ops, bin_op_nodes))

    unary_ops = _unary_ops_syms
    unary_op_nodes = 'UAdd', 'USub', 'Invert'
    unary_op_nodes_map = dict(zip(unary_ops, unary_op_nodes))

    def __init__(self, env):
        for bin_op in self.bin_ops:
            setattr(self, 'visit_{0}'.format(self.bin_op_nodes_map[bin_op]),
                    lambda node, bin_op=bin_op: partial(BinOp, bin_op))

        for unary_op in self.unary_ops:
            setattr(self,
                    'visit_{0}'.format(self.unary_op_nodes_map[unary_op]),
                    lambda node, unary_op=unary_op: partial(UnaryOp, unary_op))
        self.env = env

    def generic_visit(self, node, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, AST):
                        self.visit(item, **kwargs)
            elif isinstance(value, AST):
                self.visit(value, **kwargs)

    def visit(self, node, **kwargs):
        if not (isinstance(node, ast.AST) or isinstance(node, basestring)):
            raise TypeError('"node" must be an AST node or a string, you'
                            ' passed a(n) {0}'.format(node.__class__))
        if isinstance(node, basestring):
            node = ast.fix_missing_locations(ast.parse(node))

        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, **kwargs)

    def visit_Module(self, node, **kwargs):
        if len(node.body) != 1:
            raise ExprParserError('only a single expression is allowed')

        expr = node.body[0]
        if not isinstance(expr, ast.Expr):
            raise SyntaxError('only expressions are allowed')

        return self.visit(expr, **kwargs)

    def visit_Expr(self, node, **kwargs):
        return self.visit(node.value, **kwargs)

    def visit_BinOp(self, node, **kwargs):
        op = self.visit(node.op)
        left = self.visit(node.left,side='left')
        right = self.visit(node.right,side='right')
        return op(left, right)

    def visit_UnaryOp(self, node, **kwargs):
        if isinstance(node.op, ast.Not):
            raise NotImplementedError("not operator not yet supported")
        op = self.visit(node.op)
        return op(self.visit(node.operand))

    def visit_Name(self, node, **kwargs):
        return Term(node.id, self.env)

    def visit_Num(self, node, **kwargs):
        return Constant(node.n, self.env)

    def visit_Compare(self, node, **kwargs):
        ops = node.ops
        comps = node.comparators
        if len(ops) != 1:
            raise ExprParserError('chained comparisons not supported')
        return self.visit(ops[0])(self.visit(node.left,side='left'), self.visit(comps[0],side='right'))

    def visit_Call(self, node, **kwargs):
        if not isinstance(node.func, ast.Name):
            raise TypeError("Only named functions are supported")

        valid_ops = _reductions + _mathops

        if node.func.id not in valid_ops:
            raise ValueError("Only {0} are supported".format(valid_ops))

        raise NotImplementedError("function calls not yet supported")

    def visit_Attribute(self, node, **kwargs):
        raise NotImplementedError("attribute access is not yet supported")

    def visit_BoolOp(self, node, **kwargs):
        raise NotImplementedError("boolean operators are not yet supported")


class Expr(StringMixin):
    """Expr object"""
    def __init__(self, expr, engine='numexpr', env=None, truediv=True):
        self.expr = expr
        self.env = env or Scope(frame_level=2)
        self._visitor = ExprVisitor(self.env)
        self.terms = self.parse()
        self.engine = engine
        self.truediv = truediv

    def __call__(self, env):
        env.locals['truediv'] = self.truediv
        return self.terms(env)

    def __unicode__(self):
        return unicode(self.terms)

    def parse(self):
        """return a Termset"""
        return self._visitor.visit(self.expr)

    def align(self):
        """align a set of Terms"""
        return self.terms.align(self.env)


def isexpr(s, check_names=True):
    try:
        Expr(s)
    except SyntaxError:
        return False
    except NameError:
        return not check_names
    else:
        return True
