import re
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager


class TemplateError(Exception):
    
    pass
    
    
class TemplateSyntaxError(TemplateError):
    
    pass


class Context:
    
    def __init__(self, params, buffer=None):
        self.params = params
        self.buffer = buffer or []
    
    @contextmanager
    def block(self):
        sub_context = Context(self.params.copy(), self.buffer)
        yield sub_context
        
    def write(self, value):
        # TODO: autoescape
        self.buffer.append(str(value))
        
    def read(self):
        return "".join(self.buffer)


class Expression:
    
    def __init__(self, expression):
        self.compiled_expression = compile(expression, "<string>", "eval")
        
    def eval(self, context):
        return eval(self.compiled_expression, {}, context.params)
        
        
class Node(metaclass=ABCMeta):
    
    @abstractmethod
    def render(self, context):
        pass
        
        
class StringNode(Node):
    
    def __init__(self, value):
        self.value = value
        
    def render(self, context):
        context.buffer.append(self.value)


class ExpressionNode(Node):
    
    def __init__(self, expression):
        self.expression = Expression(expression)
        
    def render(self, context):
        context.write(self.expression.eval(context))
        
        
class Template:
    
    def __init__(self, nodes):
        self._nodes = nodes
        
    def _render_to_context(self, context):
        for node in self._nodes:
            node.render(context)
            
    def render(self, **params):
        context = Context(params)
        self._render_to_context(context)
        return context.read()


RE_TOKEN = re.compile("{#.+?#}|{{\s*(.*?)\s*}}|{%\s*(.*?)\s*%}")


def tokenize(template):
    for lineno, line in enumerate(template.splitlines(True)):
        index = 0
        for match in RE_TOKEN.finditer(line):
            # Process string tokens.
            if match.start() > index:
                yield lineno, "STRING", line[index:match.start()]
            # Process tag tokens.
            expression_token, macro_token = match.groups()
            # Process expression tokens.
            if expression_token:
                yield lineno, "EXPRESSION", expression_token
            elif macro_token:
                yield lineno, "MACRO", macro_token
            # Update the index.
            index = match.end()
        # Yield the final string token.
        yield lineno, "STRING", line[index:]


class ParserRun:

    def __init__(self, template, macros):
        self.tokens = tokenize(template)
        self.macros = macros
        
    def parse_block(self, regex=None):
        nodes = []
        for lineno, token_type, token_contents in self.tokens:
            if token_type == "STRING":
                nodes.append(StringNode(token_contents))
            elif token_type == "EXPRESSION":
                nodes.append(ExpressionNode(token_contents))
            elif token_type == "MACRO":
                # Process macros.
                node = None
                for macro in self.macros:
                    node = macro(self, token_contents)
                    if node:
                        nodes.append(node)
                        break
                if not node:
                    if regex:
                        match = regex.match(token_contents)
                        if match:
                            return lineno, match, Template(nodes)
                    raise TemplateSyntaxError("Line {lineno}: {{% {token} %}} is not a recognized tag.".format(lineno=lineno, token=token_contents))
            else:
                assert False, "{!r} is not a valid token type.".format(token_type)
        # No match.
        return lineno, None, Template(nodes)
            
        
class Parser:
    
    def __init__(self, macros=()):
        self._macros = macros
        
    def compile(self, template):
        _, _, block = ParserRun(template, list(self._macros)).parse_block()
        return block


def regex_macro(regex):
    regex = re.compile(regex)
    def decorator(func):
        def wrapper(parser, token):
            match = regex.match(token)
            if match:
                return func(parser, *match.groups(), **match.groupdict())
            return None
        return wrapper
    return decorator


class IfNode(Node):
    
    def __init__(self, clauses, else_block):
        self.clauses = clauses
        self.else_block = else_block
        
    def render(self, context):
        for expression, block in self.clauses:
            if expression.eval(context):
                block._render_to_context(context)
                return
        if self.else_block:
            self.else_block._render_to_context(context)


RE_IF_CLAUSE = re.compile("^(elif) (.+?)$|^(else)$|^(endif)$")

@regex_macro("^if\s+(.+?)$")
def if_macro(parser, expression):
    clauses = []
    else_tag = False
    else_block = None
    while True:
        lineno, match, block = parser.parse_block(RE_IF_CLAUSE)
        if else_tag:
            else_block = block
        else:
            clauses.append((Expression(expression), block))
        elif_flag, elif_expression, else_flag, endif_flag = match.groups()
        if elif_flag:
            if else_tag:
                raise TemplateSyntaxError("Line {}: {{% elif %}} tag cannot come after {{% else %}}.".format(lineno))
            expression = elif_expression
        elif else_flag:
            if else_tag:
                raise TemplateSyntaxError("Line {}: Only one {{% else %}} tag is allowed per {{% if %}} macro.".format(lineno))
            else_tag = True
        elif endif_flag:
            break
                
    return IfNode(clauses, else_block)
    
        
DEFAULT_MACROS = (if_macro,)


default_parser = Parser(DEFAULT_MACROS)