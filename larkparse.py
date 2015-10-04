import sys
from ply import *

from lark import *
import larklex

tokens = larklex.tokens

precedence = (
    ('left', 'PEVAL'),
    ('left', 'EQ', 'GT', 'LT', 'GTE', 'LTE', 'INEQ'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    # ('right', 'UMINUS'),
    ('right', 'NOT'),
)

def p_all(p):
    '''all : program expression SEMI NEWLINE
           | program expression SEMI 
           | program expression NEWLINE
           | program expression
           | program
           | expression'''
    if len(p) > 2:
        p[0] = p[1] + [p[2]]
    else:
        if isinstance(p[1], list):
            p[0] = p[1]
        else:
            p[0] = [p[1]]

def p_program(p):
    '''program : program statement
               | program NEWLINE
               | statement
               | NEWLINE'''
    if len(p) == 3:
        p[0] = p[1]
        if p[2] is not None:
            p[0] += [p[2]]
    elif p[1] is None:
        p[0] = []
    else:
        p[0] = [p[1]]

def p_statement(p):
    '''statement : expression SEMI NEWLINE
                 | expression SEMI
                 | expression NEWLINE'''
    p[0] = p[1]

def p_program_error(p):
    '''program : error'''
    p[0] = None
    p.parser.error = 1

def p_primary_expression(p):
    '''primary_expression : evaluation
                          | param_val
                          | primitive
                          | LPAREN all RPAREN'''
    if len(p) > 2:
        p[0] = ('group', p[2])
    else:
        p[0] = p[1]

def p_expression(p):
    '''expression : assignment
                  | conditional_expression
                  | additive_expression'''
    p[0] = p[1]

def p_conditional_expression(p):
    '''conditional_expression : if_start all else_ifs else all end
                              | if_start all else all end
                              | if_start all else_ifs end
                              | if_start all end''' # should include "then" here?
    if len(p) == 7:
        p[0] = ('cond-else', p[1], ('group', p[2]), p[3], ('group', p[5]))
    elif len(p) == 6:
        p[0] = ('cond-else', p[1], ('group', p[2]), ('group', p[4]))
    elif len(p) == 5:
        p[0] = ('cond', p[1], ('group', p[2]), p[3])
    else:
        p[0] = ('cond', p[1], ('group', p[2]))

def p_if_start(p):
    '''if_start : if statement 
                | if expression'''
    p[0] = p[2]

def p_else_ifs(p):
    '''else_ifs : else_ifs elif expression all
                | elif expression all'''
    if len(p) == 6:
        p[0] = p[1] + [(p[3], ('group', p[4]))]
    else:
        p[0] = [(p[2], ('group', p[3]))]


def p_additive_expression(p):
    '''additive_expression : expression PLUS expression
                           | expression MINUS expression
                           | expression TIMES expression
                           | expression DIVIDE expression
                           | expression LT expression
                           | expression EQ expression
                           | expression GT expression
                           | expression INEQ expression
                           | expression LTE expression
                           | expression GTE expression
                           | MINUS primary_expression
                           | NOT primary_expression
                           | primary_expression'''
    if len(p) == 4:
        p[0] = ('binary', p[2], p[1], p[3])
    elif len(p) == 3:
        p[0] = ('unary', p[1], p[2])
    else:
        p[0] = p[1]

# def p_multiplicative_expression(p):
    # '''multiplicative_expression : multiplicative_expression TIMES multiplicative_expression
                         # | multiplicative_expression DIVIDE multiplicative_expression
                         # | multiplicative_expression LT multiplicative_expression
                         # | multiplicative_expression LTE multiplicative_expression
                         # | multiplicative_expression GT multiplicative_expression
                         # | multiplicative_expression GTE multiplicative_expression
                         # | multiplicative_expression EQ multiplicative_expression
                         # | multiplicative_expression INEQ multiplicative_expression
                         # | unary_expression'''
    # if len(p) > 3:
        # p[0] = ('binary', p[2], p[1], p[3])
    # else:
        # p[0] = p[1]

def p_assignment(p):
    '''assignment : ID ASSIGN expression'''
    p.parser.defs[-1].add(p[1])
    p[0] = ('assign', p[1], p[3])

# def p_unary_expression(p):
    # '''unary_expression : primary_expression
                        # | MINUS primary_expression %prec UMINUS
                        # | NOT primary_expression %prec NOT'''
    # if len(p) > 2:
        # p[0] = ('unary', p[1], p[2])
    # else:
        # p[0] = p[1]

def p_param_val(p):
    '''param_val : LSQUARE param_names RSQUARE LCURLY clear_defs all RCURLY
                 | LCURLY clear_defs all RCURLY'''
    if len(p) == 5:
        p[0] = ('pval', p[3], list(p.parser.refs.pop()))
    else:
        p[0] = ('pval', p[2], p[6], list(p.parser.refs.pop() - set(p[2])))
    p.parser.defs.pop()

def p_clear_defs(p):
    '''clear_defs :'''
    p.parser.refs.append(set())
    p.parser.defs.append(set())

def p_parameters(p):
    '''parameters : parameters COMMA expression
                  | expression'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[3])

def p_param_names(p):
    '''param_names : param_names COMMA ID
                   | ID'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[3])

def p_evaluation(p):
    '''evaluation : primary_expression LSQUARE parameters RSQUARE %prec PEVAL
                  | ID'''
    if len(p) == 5:
        p[0] = ('param-eval', p[1], p[3])
    else:
        if p[1] not in p.parser.defs[-1]:
            p.parser.refs[-1].add(p[1])
        p[0] = ('evaluation', p[1])

def p_primitive(p):
    '''primitive : numval
                 | stringval
                 | boolval
                 | nilval'''
    p[0] = ('primitive', p[1])

def p_numval(p):
    '''numval : INTEGER
              | FLOAT'''
    p[0] = Val('num', eval(p[1]))

def p_stringval(p):
    '''stringval : STRING'''
    p[0] = Val('string', p[1])

def p_boolval(p):
    '''boolval : true
            | false'''
    p[0] = true if p[1] == 'true' else false

def p_nilval(p):
    '''nilval : nil'''
    p[0] = nil

def p_error(p):
    print "Syntax error: {0}".format(p)

parser = yacc.yacc()

def parse(data, debug=0):
    parser.error = 0
    parser.refs = [set()]
    parser.defs = [set()]
    parser.env = root
    p = parser.parse(data, debug=debug)
    if parser.error:
        return None
    return p

if __name__ == '__main__':
    if len(sys.argv) < 2:
        try:
            line = sys.stdin.readline()
            print parse(line)
        except KeyboardInterrupt:
            pass
    else:
        print parse(sys.argv[1])
