# -*- coding: utf-8 -*-
"""
wombat1.py Created on Mon Jun 22 10:58:33 2015

@author: Robert

The plan is to implement just enough to handle this program:

  `fact1 _n:Int>=?0 = (if _n==0 then {1} else {_n*fact1(_n-1)});
  `fact2 = { `n = $:Int>=?0; if n==0 then {1} else {n*fact2(n-1)}};
  `in = getInt();
  putInt( fact1 in = fact2 in)

The first thing is to parse it. For this we need to implement SSS for the
following operators:
  juxtapose => procedure call
  : => type coerce
  >=? => Int compare and return left arg or fail
  = => unify and return left arg or fail (same as ==? but low priority)
  () => id
  ; => last (and void earlier ones).
  if-then-else => ifP
  == => Int compare bool
  *,- => Int arith


"""

import re

# in the sop entries in sops, the 'type' is one of:
#  'initial' the op itself when it has right and no left
#  'final' a subop/op that has no right
#  'optional' an optional subop
#  'repeat' a subop that can repeat
#  'required' a mandatory subop (the op is always required)
#  'solo' an op with no left or right: the same as an id
#  'infix' an infix operator

# 'left' and 'right' default to none. For subops, default type is 'mandatory',
ops = {
    "!!SOF" : { 'action':'identity','sops': [{'sop':'!!SOF','type':'initial'},
                                   {'sop':'!!EOF','type':'final'}]},
    " " : {'left':1000,'action':'call',
           'sops': [{'sop':' ','type':'infix','right':999}]}, #loose concat
    "" : {'left':1000,'action':'call',
          'sops':[{'sop':'','type':'infix','right':999}]}, #tight concat
    ":" : {'left':2000,'action':'toType',
           'sops':[{'sop':':','type':'infix','right':500}]},
    ">=?" : {'left':100, 'action':'geOrFail',
             'sops':[{'sop':'>=?','type':'infix','right':101}]}, # right
    '(' : { 'action':'identity','sops':[{'sop':'(','type':'initial'},
                              {'sop':')','type':'final'}]}, # no left or right
    "=" : {'left':20,'action':'unify',
           'sops':[{'sop':'=','type':'infix','right':20}]},
    "if" : {'action':'ifP','sops':[{'sop':'if','type':'initial'}, 
                               {'sop':'then','type':'required','right':10},
                               {'sop':'else','type':'optional','right':10}]},
    "==" : {'left':100, 'action':'eq',
            'sops':[{'sop':'==','type':'infix','right':100}]},
    "{" : {'action':'closure','sops':[{'sop':'{','type':'initial'},
                                  {'sop':'}','type':'final'}]},
    "*" : {'left':400, 'action':'product',
           'sops':[{'sop':'*','type':'infix','right':400}]},
    "-" : {'left':300, 'action':'minus',
           'sops':[{'sop':'-','type':'infix','right':299}]},
    ";" : {'left':1, 'action':'last',
           'sops':[{'sop':';','type':'infix','right':1}]},
    "$" : {'action':'parameter','sops':[{'sop':'$','type':'solo'}]},
}

#FIXME: Should assert that ops and opSops are sane.

defs = { # defs act as solo ops
    'Int' : {'type':'Type', 'val':'Int'},
    '0' : {'type':'Int', 'val':0},
    '1' : {'type':'Int', 'val':1},
    'getInt' : {'type': 'Unit->Int', 'val':'getInt'},
    'putInt' : {'type': 'Int->Unit', 'val':'putInt'},
    'unit' : {'type':'Unit','val':'unit'}
}

prog = '''
  `fact1 _n = (if (_n:Int>=?0)==0 then {1} else {_n*fact1(_n-1)});
  `fact2 = { `n = $:Int>=?0; if n==0 then {1} else {n*fact2(n-1)}};
  `in = getInt();
  putInt( fact1 in = fact2 in)
'''
#prog = "0 * 1 - 2 * 3"

# currently 4 categories:
#   ` can precede anything
#   single characters: ()[]{}
#   simple ids: [$a-zA-Z0-9_]+
#   a seq of other chars
# So we have optional `, then one of other 3, then whitespace or other
#   singch = r'[()[\]{}]'
#   idch = r'[$a-zA-Z0-9_]'
#   othch = r'[^()[\]{}$a-zA-Z0-9_]'

# tokIter yieldss pairs of tokens and "" or " " depending on whether
# followed by whitespace.
def tokIter(code,n):
    yield ("!!SOF","") # ignore initial whitespace
    n += (re.match(r'\s*',code)).end()
    while(n<len(code)):
        mt = re.match(r'[`]?[$a-zA-Z0-9_]+',code[n:])
        if not mt : 
            mt = re.match(r'[`]?[()[\]{}]',code[n:])
        if not mt :
            mt = re.match(r'[`]?[^\s()[\]{}$a-zA-Z0-9_]+',code[n:])
        n += mt.end()
        mw = re.match(r'\s*',code[n:])
        w = " " if mw.group(0) != "" else ""
        n += mw.end()
        yield (mt.group(0),w)
            
    yield ("!!EOF","")
    yield ("!!ignore","") # should never see this

toks = [tok for tok in tokIter(prog,0)]

def tokOnly(ind):
    tok,_ = toks[ind]
    return tok
# note that a Wombat identifier (with possible ` or _) is just an operator with
# no left or right
def sopsInPlay(sops,sopi):
    for i in range(sopi,len(sops)):
        yield sops[i]
        if sops[i]['type']=='required': # sops beyond this are not in play
            return

def hasLeft(tok):
    return tok in ops and 'left' in ops[tok]

def hasRight(sop):
    return sop!=None and sop['type'] not in ['final','solo']

def tokInSops(tok,sops):
    for s in sops: 
        if s['sop']==tok: 
            return True
    return False
    
# the active operator is the one that called us. 
# must start at something with no left, else insert unit
def getExpr(curr,left,prio,sopsExpected,upAst):
    tokC,brkC = toks[curr] # tokC points to subop, initially op
    # if there is no ops[tok] it should be an identifier which
    #  has no left or right.
    
    # if left absent, the first thing has to have no left.
    if left==None and (tokInSops(tokC,sopsExpected) or hasLeft(tokC)):
        # need no-left so stick in a unit
        toks.insert(curr,("unit",""))
        tokC,brkC = "unit",""

    # Now tokC definitely doesn't point to a subop.
    
    # Note that we can't have a subop at this point, just an op or identifier
    # (and the op can't be " " which is only infix or subop).
    # We don't know yet which version of a name we have: so it's just an op.
    op = ops[tokC] if tokC in ops else \
                    {'action':'name','sops':[{'sop':tokC,'type':'solo'}]}
    assert tokC == op['sops'][0]['sop']
    rParamsLen = len(op['sops']) - (1 if op['sops'][-1]['type'] in ['final','solo'] else 0)
    asTree = {'op':op, 'lParam':left, 'rParams':rParamsLen*[None], 'parent':upAst}
    if left!=None: 
        left['parent'] = asTree
    # We now have to get the parameters for asTree. Each parameter will
    # be terminated by (A) one of my expected subops; (B) some higher
    # expected subop (ending all my subops); (C) an operator whose
    # left priority is less than my current subop's right prioity.
    for sopi in range(0, len(op['sops'])):
        # initially sop is the op, so we start in sync
        sop = op['sops'][sopi] # subop last seen
        sopType = sop['type']
        if sopType in ['repeat','optional']:
            assert asTree['rParams'][sopi] == None
            asTree['rParams'][sopi] = [] # opt or rep added here
        myExpSops = list(sopsInPlay(op['sops'],sopi+1))
        while True: # keep coming back here if repeat, all else does break
            if tokC!=sop['sop']:
                # gone past this optional/repeat subop
                assert sopType in ['repeat','optional']
                break # = continue of for loop
            nexti = curr+1
            tokN,_ = toks[nexti]
            if sopType in ['final','solo']:
                # this is where we might need to insert a " " or "" (sub)op
                if not tokInSops(tokN,sopsExpected) and (tokN not in ops or 'left' not in ops[tokN]):
                    toks.insert(nexti,(brkC,""))
                    tokN = brkC
                # Now every op that has no left(/right) is preceded(/followed) by
                # an op with a right(/left) to munch it (or munch a bigger expression 
                # ending(/starting) with it). We just need to sort out the priorities.
                assert myExpSops == []
                assert tokInSops(tokN,sopsExpected) or (tokN in ops and 'left' in ops[tokN])
                #if prio > ops[tokN]['left']:
                return asTree,nexti
                #else:
                #    return getExpr(nexti,asTree,prio,sopsExpected,upAst)
            # not final or solo so something to get for sop
            assert not tokInSops(tokN,sopsExpected) # or would have inserted unit
            assert hasRight(sop) # since returned if solo or final
            needMySop = any(map(lambda s:s['type'] in ['required','final'], myExpSops))
            expSops = myExpSops+([] if needMySop else sopsExpected)
            pRprio = (sop['right'] if 'right' in sop else -1)
            pexp,nexti = getExpr(nexti, None, pRprio, expSops, asTree)
            # after a getExpr we end with no right, so following has a left
            tokN,_ = toks[nexti]        
            while not tokInSops(tokN,expSops) and pRprio < ops[tokN]['left']:
                pexp,nexti = getExpr(nexti, pexp, pRprio, expSops, asTree)
                tokN,_ = toks[nexti]
            if asTree['rParams'][sopi] != None: # repeat or optional
                asTree['rParams'][sopi].append(pexp)
            else:
                asTree['rParams'][sopi] = pexp
            # We end up with nexti pointing to the subop that we finished on,
            # or the op whose lower left priority stopped us.
            curr = nexti # points to our next actual subop (or it doesn't matter)
            tokC,_ = toks[curr]
            if sopType != 'repeat':
                break
    return asTree,nexti

def expr2SExp(e):
    op = e['op']['sops'][0]['sop']
    se ='("'+op+'"'
    if e['lParam'] != None:
        se += ' '+expr2SExp(e['lParam'])
    for i in range(0,len(e['rParams'])):
        if isinstance(e['rParams'][i],list):
            se += ' ['+(" ".join([expr2SExp(k) for k in e['rParams'][i]]))+"]"
        else:
            se += ' '+expr2SExp(e['rParams'][i])
    return se+')'


parsed,_ = getExpr(0,None,-1,[],None)
pse = expr2SExp(parsed)
print(pse)
