from ply import *

keywords = (
    'if', 'then', 'else', 'elif', 'end', #'for','break','continue',
    'true','false','nil'
)

tokens = keywords + (
     'EQ','INEQ','PLUS','MINUS','TIMES','DIVIDE',
     'LPAREN','RPAREN','LCURLY','RCURLY','LSQUARE','RSQUARE',
     'LT','LTE','GT','GTE',
     'NOT','ASSIGN','HAT',
     #'COMMA','SEMI',
     'INTEGER','FLOAT', 'STRING',
     'ID','SEMI','NEWLINE','COMMA'
)

t_ignore = ' \t'

def t_comment(t):
    r"[ ]*\043[^\n]*"  # \043 is '#'
    pass

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    if t.value in keywords:
        t.type = t.value
    return t

t_ASSIGN  = r'='
t_HAT     = r'\^'
t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_LSQUARE = r'\['
t_RSQUARE = r'\]'
t_LCURLY  = r'\{'
t_RCURLY  = r'\}'
t_LT      = r'<'
t_LTE     = r'<='
t_GT      = r'>'
t_GTE     = r'>='
t_INEQ    = r'!='
t_NOT     = r'!'
t_EQ      = r'=='
t_COMMA   = r'\,'
t_SEMI    = r';'
t_INTEGER = r'\d+'
t_FLOAT   = r'((\d*\.\d+)(E[\+-]?\d+)?|([1-9]\d*E[\+-]?\d+))'

def t_STRING(t):
    r'(\".*?\")|(\'.*?\')'
    if t.value.startswith("'"):
        t.value = t.value.strip("'")
    else:
        t.value = t.value.strip('"')
    return t

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

def t_error(t):
    print("Illegal character %s" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex(debug=0)
if __name__ == "__main__":
    lex.runmain(lexer)
