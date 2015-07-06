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

# 'left' and 'right' default to none. For subops, default type is 'required',
ops = {}
ops["!!SOF"] = { 'subops':[{'subop':'!!EOF'}], 'op':'id'}
#ops['`'] = {'op':'defNext'}
ops[" "] = {'left':1000,'right':999,'op':'call'} #loose concat
ops[""] = ops[" "] #tight concat
ops[":"] = {'left':2000,'right':500,'op':'toType'}
ops[">=?"] = {'left':100,'right':100, 'op':'geOrFail'} # should be assoc
ops['('] = { 'subops':[{'subop':')'}], 'op':'id'} # no left or right
ops["="] = {'left':20,'right':20,'op':'unify'}
ops["if"] = {'right':10,'subops':[{'subop':'then'},
                                  {'subop':'else','type':'opt'}],'op':'ifP'}
ops["=="] = {'left':100,'right':100, 'op':'eq'}
ops["{"] = {'subops':[{'subop':'}'}], 'op':'closure'}
ops["*"] = {'left':400,'right':400, 'op':'product'}
ops["-"] = {'left':300,'right':299, 'op':'minus'}
ops[";"] = {'left':1,'right':1, 'op':'last'}
ops["$"] = {'op':'parameter'}

defs = {}
defs['Int'] = {'type':'Type', 'val':'Int'}
defs['0'] = {'type':'Int', 'val':0}
defs['1'] = {'type':'Int', 'val':1}
defs['getInt'] = {'type': 'Unit->Int', 'val':'getInt'}
defs['putInt'] = {'type': 'Int->Unit', 'val':'putInt'}
defs['unit'] = {'type':'Unit','val':'unit'}

prog = '''
  `fact1 _n:Int>=?0 = (if _n==0 then {1} else {_n*fact1(_n-1)});
  `fact2 = { `n = $:Int>=?0; if n==0 then {1} else {n*fact2(n-1)}};
  `in = getInt();
  putInt( fact1 in = fact2 in)
'''

# currently 4 categories:
#   ` can precede anything
#   single characters: ()[]{}
#   simple ids: [$a-zA-Z0-9_]+
#   a seq of other chars
# So we have optional `, then one of other 3, then whitespace or other
singch = r'[()[\]{}]'
idch = r'[$a-zA-Z0-9_]'
othch = r'[^()[\]{}$a-zA-Z0-9_]'

# tokIter yieldss pairs of tokens and "" or " " depending on whether
# followed by whitespace.
def tokIter(code,n):
    yield ("!!SOF","") # ignore initial whitespacex
    n += (re.match(r'\s*',code)).end()
    while(n<len(code)):
        mt = re.match(r'[`]?[$a-zA-Z0-9_]+',code[n:])
        if not mt : 
            mt = re.match(r'[`]?[()[\]{}]',code[n:])
        if not mt :
            mt = re.match(r'[`]?[^\s()[\]{}$a-zA-Z0-9_]+',code[n:])
        n += mt.end()
        mw = re.match(r'\s*',code[n:])
        if mw.group(0) != "":
            w = " "
        else:
            w = ""
        n += mw.end()
        yield (mt.group(0),w)
            
    yield ("!!EOF","")

toks = [tok for tok in tokIter(prog,0)]

# note that an identifier (with ` or _) is just an operator with no left 
# or right
def getExpr(actv,curr,stackOfSubops):
    # we'll ignore the value of brk since our example doesn't use
    # the tight/loose concatenation distinction
    aParams = []
    tokA,brkA = toks[actv]
    aSubopIndex = 0 # if any
    tokC,brkC = toks[curr]
    # the first thing has to have no left.
    if ops[tokC]!=None and ops[tokC]['left']!=None:
        # no left so stick in a unit
        toks.insert(curr,("unit",""))
        tokC,brkC = ("unit","")
    tokN,brkN = toks[curr+1]
    # NORIGHT:
    if ops[tokC]==None or ops[tokC]['right']==None:
        if ops[tokA]!=None and ops[tokA]['subops']!=None and \
        ops[tokN]==ops[tokA]['subops'][aSubopIndex]:
            
    

parsed = getExpr(0,1,[(0,'!!EOF')])
    
