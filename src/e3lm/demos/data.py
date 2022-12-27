examples = []

def getcode(num, prefix="code"):
    code = globals().get(prefix + str(num), "")
    if code != "":
        return code
    else:
        return None

# 0
code0 = """\
; Empty block
Dummy dummy
End
"""
examples.append({"text": code0,
                 "lex": {
                     "assert": [
                         ["tokens", ['CLASS', 'NAME', 'END']]
                     ]},
                 })
# 1
code1 = """; Nested empty blocks
Dummy dummy_1
End
Dummy dummy_2
    Dummy dummy_2_1
        Dummy dummy_2_1_1
            Dummy dummy_2_1_1_1
            End
        End
    End
End
Dummy ;unnamed
End
"""
examples.append({"text": code1,
                 "lex": {
                     "assert": [
                         ["tokens", ['CLASS', 'NAME', 'END', 'CLASS', 'NAME',
                                     'CLASS', 'NAME', 'CLASS', 'NAME', 'CLASS',
                                     'NAME', 'END', 'END', 'END', 'END',
                                     'CLASS', 'END']],
                     ]},
                 "dot": True,
                 })
# 2
code2 = """Dummy dummy_1
    Dummy dummy_1_1
        Dummy dummy_1_1_1
            ; Basic attributes' expressions
            attr1 = 0
            attr2 = 0.0
            attr3 = 0o0
            attr4 = 0x0
            attr5 = 0b0
            attr6 = 3j
            attr7 = 5 + 3.14e-10j
            attr8 = "Q2 String"
            attr9 = 'Q1 String'
            attr10 = \"\"\"TQ2 String\"\"\"
            attr11 = '''TQ1 String'''
            attr12 = None
            attr13 = True
            attr14 = False
            attr15 = \"\"\"TQ2 w\\ quotes: '" I guess\"\"\"
        End
        Dummy dummy_1_1_2
            ; Arithmetic expressions
            attr1 = 0+1
            attr2 = 0.0 + 0.1
            attr3 = 0o5 + 0o11
            attr4 = 0x5 + 0x9
            attr5 = 0b1 + 0b111
            attr6 = 3j + 15j
            attr7 = (5 + 3j) + (10 + 2j)
            attr8 = "Q2" + ' ' + '''TQ1'''
            attr9 = 5 * 2
            attr10 = 11 / 10
            attr11 = 11 // 10
            attr12 = 5 - 5
        End
        Dummy dummy_1_1_3
            ; Complicated attributes
            attr1 = prev()
            attr2 = {
                1: {2: {"hi": "hello"}}
            }
            attr3 = attr2
            attr4 = next().attr2["two"]
            attr5 = body
            attr6 = prev(Dummy).attr1
            attr7 = Dummy
            attr8 = (5 - (attr4+5) + 5)
            attr9 = attr8 + prev().attr7
            attr10 = - attr8
            attr11 = dummy_1_1_4
            attr12 = attr11.attr1
            attr13 = next(Dummy)
            attr14 = dummy_1_1_4.attr0
            ;TODO: interpreter error: attr15 = attr14.attr0
            ---
             Bodytext
            ---
        End
        Dummy dummy_1_1_4
            attr0 = "5"
            ; Arrays and Dicts
            attr1 = prev().attr1.attr1
            attr2 = {
                "one": attr1,
                "two": 2
            }
            attr3a = [
                "Hi", "There", {"one": 1},
            ]
            attr4 = attr3a[2]["one"]
        End
    End
End
Object
End
"""
examples.append({"text": code2,
                 "lex": True,
                 "parse": True,
                 "interpret": {
                     "assert": [
                         ["dummy_1_1_3.body", "Bodytext"],
                         ["dummy_1_1_2.attr1", 1],
                         ["dummy_1_1_2.attr8", "Q2 TQ1"],
                     ]},
                 "json": True,
                 })
# 3
errorcode0 = """\
Dummy dummy_1_1
;comment
    attr0 = 0
     attr1 = 1
   attr2 = 0
End
"""
examples.append({"text": errorcode0,
                 "lex": {
                     "assert": [
                         ["error", {"class": "IndentationError", "lineno": 3}],
                     ]},
                 })
# 4
errorcode1 = """\
Dummy dummy_2_1
    Dummy
        Dummy dummy_2_2
    attr1 = 0
            attr2 = 0
        ---
    what
       ---
    End
        End
  End
"""
examples.append({"text": errorcode1,
                 "lex": {
                     "assert": [
                         ["error", {"class": "IndentationError", "lineno": 4}],
                     ]},
                 "parse": True,
                 })
# 5
errorcode2 = """\
Dummy dummy_2
        Dummy
    Dummy
;comment
     attr = 1
     attr = 2
    ---
what
    ---
End
    End
End
"""
examples.append({"text": errorcode2,
                 "lex": True,
                 "parse": {
                     "assert": [
                         ["p_error", {"class": "AttributeError", "lineno": 0}],
                         ["p_error", {"class": "SyntaxError", "lineno": 7}],
                     ]},
                 })
# 6
code3 = """\
Dummy dummy_1
    attr1 = attr2
    attr2 = 2
    attr3 = name
End
Dummy d
    attr1 = prev().name
    attr2 = prev(Dummy)
    attr3 = prev(Dummy).name
    attr5 = "word".join(attr4)
    ---rtl
    مرحبا
    بكم
    في
    مكتبة
    كنان
    ---
    attr4 = body.split("\\n")
End

Dummy e232
    body = ""
End

; comment?
"""
examples.append({"text": code3,
                 "lex": True,
                 })
# 7
code4 = """\
Dummy my1
    attr2 = {
        0: {
            "1": {
                "2": {
                    "hi": "hello"
                }
            }
        }
    }
    attr1 = attr2[0]["1"]["2"]["hi"]

End
"""
examples.append({"text": code4,
                 "lex": True,
                 })
# 8
code5 = """\
Dummy dummy_1
    attr1 = 1.0
    attr2 = 5.0
    attr1_unit = "cm"
    attr2_unit = "m"
End
"""
examples.append({"text": code5,
                 "interpret": True,
                 "units": {
                     "assert": [
                         ["dummy_1.attr1.unit.id", "cm"]
                     ]},
                 })
