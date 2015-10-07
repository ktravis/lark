import sys
from ply import *

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

# def p_program_error(p):
    # '''program : error'''
    # p[0] = None
    # p.parser.error = 1

def p_primary_expression(p):
    '''primary_expression : evaluation
                          | param_val
                          | dot_op
                          | primitive
                          | LPAREN NEWLINE all NEWLINE RPAREN
                          | LPAREN NEWLINE all RPAREN
                          | LPAREN all NEWLINE RPAREN
                          | LPAREN all RPAREN'''
    if len(p) == 6:
        p[0] = ('group', p[3])
    elif len(p) == 5:
        if p[2] is None:
            p[0] = ('group', p[3])
        else:
            p[0] = ('group', p[2])
    elif len(p) == 4:
        p[0] = ('group', p[2])
    else:
        p[0] = p[1]

def p_ref(p):
    '''ref : HAT ID'''
    p[0] = ('ref', p[2])

def p_expression(p):
    '''expression : assignment
                  | conditional_expression
                  | loop_expression
                  | tuple
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

def p_loop_expression(p):
    '''loop_expression : loop expression all end'''
    p[0] = ('loop', p[2], p[3])

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

def p_assignment(p):
    '''assignment : HAT ID ASSIGN expression
                  | dot_op ASSIGN expression
                  | ID ASSIGN expression'''
    if len(p) == 4:
        if isinstance(p[1], basestring):
            p.parser.defs[-1].add(p[1])
            p[0] = ('assign', p[1], p[3])
        else:
            p[0] = ('member-assign', p[1], p[3])
    else:
        p.parser.refs[-1].add(p[2])
        p[0] = ('upval-assign', p[2], p[4])

def p_op_assign(p):
    '''assignment : ID assignment_op expression
                  | dot_op assignment_op expression'''
    if isinstance(p[1], basestring):
        if p[1] not in p.parser.defs[-1]:
            p.parser.refs[-1].add(p[1])
    p[0] = ('op-assign', p[2][0], p[1], p[3])

def p_assignment_op(p):
    '''assignment_op : PLUS_ASSIGN
                     | MINUS_ASSIGN
                     | TIMES_ASSIGN
                     | DIVIDE_ASSIGN'''
    p[0] = p[1]

def p_param_val(p):
    '''param_val : LSQUARE param_names RSQUARE LCURLY clear_defs all RCURLY
                 | LCURLY clear_defs all RCURLY'''
    if len(p) == 5:
        p[0] = ('pval', p[3], list(p.parser.refs.pop()))
    else:
        p[0] = ('pval', p[2], p[6], list(p.parser.refs.pop() - set(p[2])))
    p.parser.defs.pop()

def p_dot_op(p):
    '''dot_op : primary_expression DOT LPAREN expression RPAREN
              | primary_expression DOT ID
              | primary_expression DOT INTEGER'''
    if len(p) == 6:
        p[0] = ('indirect-dot', p[1], p[4])
    else:
        v = p[3]
        try:
            v = int(v)
        except ValueError:
            pass
        p[0] = ('dot', p[1], v)


def p_clear_defs(p):
    '''clear_defs :'''
    p.parser.refs.append(set())
    p.parser.defs.append(set())

def p_parameters(p):
    '''parameters : parameters tuple_sep expression
                  | expression'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[3])

def p_param_names(p):
    '''param_names : param_names tuple_sep ID
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
    p[0] = ('num', eval(p[1]))

def p_tuple(p):
    '''tuple : tuple_contents NEWLINE RPAREN
             | tuple_contents RPAREN
             | tuple_start NEWLINE RPAREN
             | tuple_start RPAREN'''
    p[0] = ('tuple', p[1])

def p_tuple_contents(p):
    '''tuple_contents : tuple_contents tuple_sep labelled_member
                      | tuple_contents tuple_sep expression
                      | tuple_start labelled_member
                      | tuple_start expression'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = p[1] + [p[2]]

def p_member_label(p):
    '''member_label : LPAREN additive_expression RPAREN
                    | ID'''
    if len(p) == 4:
        p[0] = ('member-label', p[2])
    else:
        p[0] = ('member-label-literal', p[1])

def p_tuple_start(p):
    '''tuple_start : LPAREN NEWLINE labelled_member tuple_sep
                   | LPAREN NEWLINE expression tuple_sep
                   | LPAREN labelled_member tuple_sep
                   | LPAREN expression tuple_sep'''
    if len(p) == 5:
        p[0] = [p[3]]
    else:
        p[0] = [p[2]]

def p_labelled_member(p):
    '''labelled_member : member_label COLON NEWLINE expression
                    | member_label COLON expression'''
    if len(p) == 5:
        p[0] = ('named-member', p[1], p[4])
    else:
        p[0] = ('named-member', p[1], p[3])

def p_tuple_sep(p): # optional newline
    '''tuple_sep : tuple_sep NEWLINE
                 | COMMA'''
    p[0] = ','

def p_stringval(p):
    '''stringval : STRING'''
    p[0] = ('string', p[1])

def p_boolval(p):
    '''boolval : true
            | false'''
    p[0] = ('bool', True) if p[1] == 'true' else ('bool', False)

def p_nilval(p):
    '''nilval : nil'''
    p[0] = ('nil')

def p_error(p):
    raise Exception("Syntax error: {0}".format(p))

parser = yacc.yacc()

def parse(data, debug=0):
    parser.error = 0
    parser.refs = [set()]
    parser.defs = [set()]
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
