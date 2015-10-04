import sys
from ply import *

from lark import *
import larklex

tokens = larklex.tokens

precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('left', 'EQ', 'INEQ'),
    ('right', 'ASSIGN'),
    ('right', 'UMINUS'),
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
    '''primary_expression : param_val
                          | evaluation
                          | primitive
                          | LPAREN expression RPAREN'''
    if len(p) > 2:
        p[0] = p[2]
    else:
        p[0] = p[1]

def p_expression(p):
    '''expression : assignment
                  | additive_expression
                  | multiplicative_expression'''
    p[0] = p[1]

def p_additive_expression(p):
    '''additive_expression : additive_expression PLUS multiplicative_expression
                           | additive_expression MINUS multiplicative_expression
                           | multiplicative_expression'''
    if len(p) > 2:
        p[0] = ('binary', p[2], p[1], p[3])
    else:
        p[0] = p[1]

def p_multiplicative_expression(p):
    '''multiplicative_expression : multiplicative_expression TIMES unary_expression
                         | multiplicative_expression DIVIDE unary_expression
                         | multiplicative_expression LT unary_expression
                         | multiplicative_expression LTE unary_expression
                         | multiplicative_expression GT unary_expression
                         | multiplicative_expression GTE unary_expression
                         | multiplicative_expression EQ unary_expression
                         | multiplicative_expression INEQ unary_expression
                         | unary_expression'''
    if len(p) > 2:
        p[0] = ('binary', p[2], p[1], p[3])
    else:
        p[0] = p[1]

# def p_assignment(p):
    # '''assignment : id_assign expression'''
    # p.parser.defs[-1].add(p[1])
    # p[0] = ('assign', p[1], p[3])

def p_assignment(p):
    '''assignment : ID ASSIGN expression'''
    p.parser.defs[-1].add(p[1])
    p[0] = ('assign', p[1], p[3])

# def p_id_assign(p):
    # '''id_assign : ID ASSIGN'''
    # p[0] = p.parser.env.getlocal_ormakeref(p[1])

def p_unary_expression(p):
    '''unary_expression : primary_expression
                        | MINUS primary_expression %prec UMINUS
                        | NOT primary_expression %prec NOT'''
    if len(p) > 2:
        p[0] = ('unary', p[1], p[2])
    else:
        p[0] = p[1]

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
    '''evaluation : expression LSQUARE parameters RSQUARE
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
