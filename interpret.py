import xml.etree.ElementTree as ET
import sys
import re
import operator

inputfile = sys.stdin
sourcefile = sys.stdin
outputfile = ''
statistic = []
varscount = 0
instscount = 0
isstats = False
symbol_regex = '^(var@(GF|LF|TF)@[a-zA-Z\-_$&%*!?][a-zA-Z0-9\-_$&%*!?]*)|(nil@nil)|(int@[+|-]?[0-9]+)|(bool@(true|false))|(string@(\S)*)$'
varregex = "^(GF|LF|TF)@[a-zA-Z-_$&%*!?][a-zA-Z0-9-_$&%*!?]*$"
stringregex = "^string@(\S)+$"
boolregex = "^bool@(true|false)$"
intregex = "^int@[+|-]?[0-9]+"
var = {}
varLF = {}
varTF = {}
labels = {}
localframe = False
tempframe = False
calculate = []
ops = {"+": operator.add, "-": operator.sub, "/": operator.floordiv, "*": operator.mul,
       "<": operator.lt, ">": operator.gt, "=": operator.eq, "!=": operator.ne}
index = 0
returnIndex = 0
callWasUsed = False

stack = []

LFBoolStack = []
LFBoolStack.append(False)

LFStack = []
LFStack.append(0)

callStack = []
callStack.append(False)

callStackIndex = []
callStackIndex.append(-1)


class ErrorHandling:
    def __init__(self, message, code):
        self.message = message
        self.code = code

    @classmethod
    def error_exit(cls, message, code):
        sys.stderr.write(message)
        exit(code)


Error = ErrorHandling


def parseArguments():
    global inputfile
    global sourcefile
    global outputfile
    global statistic

    isinput = False
    issource = False
    global isstats
    firsttime = True

    for arg in sys.argv:
        if firsttime:
            firsttime = False
        elif arg == '--help':
            if len(sys.argv) != 2:
                Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                                 "PRE NAPOVEDU NAPISTE --help\n", 10)
            printHelp()

        elif re.match(r"^--input=\S+$", arg):
            if isinput:
                Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                                 "PRE NAPOVEDU NAPISTE --help\n", 10)
            inputfile = arg.partition('=')[2]
            isinput = True

        elif re.match(r"^--source=\S+$", arg):
            if issource:
                Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                                 "PRE NAPOVEDU NAPISTE --help\n", 10)
            sourcefile = arg.partition('=')[2]
            issource = True

        elif re.match(r"^--stats=\S+$", arg):
            if isstats:
                Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                                 "PRE NAPOVEDU NAPISTE --help\n", 10)
            outputfile = arg.partition('=')[2]
            isstats = True

        elif arg == '--insts':
            statistic.append('--insts')

        elif arg == '--vars':
            statistic.append('--vars')

        else:
            Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                             "PRE NAPOVEDU NAPISTE --help\n", 10)

    if not issource and not isinput:
        Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                         "PRE NAPOVEDU NAPISTE --help\n", 10)

    if len(statistic) != 0 and not isstats:
        Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                         "PRE NAPOVEDU NAPISTE --help\n", 10)


def printHelp():
    print("THIS IS HELP\n")
    exit(0)


def controlFlowForArgs1(args):
    final = []
    for arg in args:
        if arg.tag == 'arg1':
            final.insert(0, arg)
        else:
            Error.error_exit("BAD XML!\n",32)

    for arg in list(args):
        args.remove(arg)
    args.append(final[0])


def controlFlowForArgs2(args):
    final = []

    for arg in args:
        if arg.tag == 'arg1':
            final.insert(0, arg)
        elif arg.tag == 'arg2':
            final.insert(1, arg)
        else:
            Error.error_exit("BAD XML!\n", 32)

    for arg in list(args):
        args.remove(arg)

    args.append(final[0])
    args.append(final[1])


def controlFlowForArgs3(args):
    final = []
    for arg in args:
        if arg.tag == 'arg1':
            final.insert(0, arg)
        elif arg.tag == 'arg2':
            final.insert(1, arg)
        elif arg.tag == 'arg3':
            final.insert(2, arg)
        else:
            Error.error_exit("BAD XML!\n", 32)

    for arg in list(args):
        args.remove(arg)

    args.append(final[0])
    args.append(final[1])
    args.append(final[2])


def parseXML(child):
    global varTF
    global varLF
    global tempframe
    global localframe
    global callStackIndex
    args = []
    opcode = list(child.attrib.values())[1].upper()
    argumentcount = len(child)
    global index
    global callWasUsed
    global instscount

    localframe = LFBoolStack[len(LFBoolStack)-1]

    if opcode == 'CREATEFRAME':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        varTF = {}
        tempframe = True
        instscount += 1
        return

    if opcode == 'PUSHFRAME':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        if not tempframe:
            Error.error_exit("PRISTUP K NEDEFINOVANEMU RAMCI PUSHFRAME!\n", 55)
        varLF = varTF
        varTF = {}
        for item in list(varLF.keys()):
            if re.match(r"TF@\S", item):
                string = item.split('@', 1)[1]
                varLF[f'LF@{string}'] = varLF.pop(f'TF@{string}')
        LFStack.append(varLF)
        LFBoolStack.append(True)
        tempframe = False
        instscount += 1
        return

    if opcode == 'POPFRAME':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        if not localframe:
            Error.error_exit("PRISTUP K NEDEFINOVANEMU RAMCI POPFRAME!\n", 55)

        varTF = LFStack.pop()
        for item in list(varTF.keys()):
            if re.match(r"LF@\S", item):
                string = item.split('@', 1)[1]
                varTF[f'TF@{string}'] = varTF.pop(f'LF@{string}')

        LFBoolStack.pop()
        varLF = LFStack.pop()
        LFStack.append(varLF)
        tempframe = True
        instscount += 1
        return

    if opcode == 'RETURN':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        if len(callStack) <= 0:
            Error.error_exit("CALL NEBOL POUZITY!\n", 56)
        index = callStackIndex.pop()
        callStack.pop()
        instscount += 1
        return

    if opcode == 'ADDS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        arithmeticsS('+')
        instscount += 1
        return

    if opcode == 'IDIVS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        arithmeticsS('/')
        instscount += 1
        return

    if opcode == 'MULS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        arithmeticsS('*')
        instscount += 1
        return

    if opcode == 'SUBS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        arithmeticsS('-')
        instscount += 1
        return

    if opcode == 'EQS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        compareS('=')
        instscount += 1
        return

    if opcode == 'LTS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        compareS('>')
        instscount += 1
        return

    if opcode == 'GTS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        compareS('<')
        instscount += 1
        return

    if opcode == 'ANDS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        logicalS('=')
        instscount += 1
        return

    if opcode == 'ORS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        logicalS('or')
        instscount += 1
        return

    if opcode == 'NOTS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        logicalSnot('not')
        instscount += 1
        return

    if opcode == 'STRI2INTS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        stri2intS()
        instscount += 1
        return

    if opcode == 'INT2CHARS':
        if argumentcount != 0:
            Error.error_exit("BAD XML!\n", 32)
        int2charS()
        instscount += 1
        return

    if argumentcount == 0:
        Error.error_exit("BAD XML!\n", 32)

    if argumentcount == 3:
        controlFlowForArgs3(child)
    if argumentcount == 2:
        controlFlowForArgs2(child)
    if argumentcount == 1:
        controlFlowForArgs1(child)

    for arg in child:
        args.append(arg)
        functions(opcode, arg, argumentcount)
        # arg.tag == arg1, arg2 atd
        # arg.text == GF@a, 5, string, true, false....
        # arg.attrib.values()[0] == var, bool, string, int,...


def functions(opcode, arg, argumentcount):
    global varTF
    global varLF
    global tempframe
    global localframe
    argtype = list(arg.attrib.values())[0]
    global index
    global returnIndex
    global callStackIndex
    global stack
    global instscount
    global varscount

    if opcode == 'DEFVAR':
        controlRightCountOfArguments(argumentcount, 1)
        if not re.match(r"{}".format(varregex), arg.text):
            Error.error_exit("WRONG FORMAT FOR DEFVAR!\n", 53)
        if arg.text[0:2] == 'LF':
            if not localframe:
                Error.error_exit("PRISTUP K NEDEFINOVANEMU RAMCI DEFVAR!\n", 55)
            if arg.text in varLF:
                Error.error_exit("REDEFINITION OF VARIABLE!\n", 52)
            varLF.update({arg.text: ""})
        elif arg.text[0:2] == 'TF':
            if not tempframe:
                Error.error_exit("PRISTUP K NEDEFINOVANEMU RAMCI DEFVAR!\n", 55)
            if arg.text in varTF:
                Error.error_exit("REDEFINITION OF VARIABLE!\n", 52)
            varTF.update({arg.text: ""})
        elif arg.text in var:
             Error.error_exit("REDEFINITION OF VARIABLE!\n", 52)
        if arg.text[0:2] == 'GF':
            var.update({arg.text: ""})
        if arg.text[0:2] == 'TF':
            varTF.update({arg.text: ""})
        if arg.text[0:2] == 'LF':
            varLF.update({arg.text: ""})
        instscount += 1
        varscount += 1

    elif opcode == 'MUL':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('*')
        instscount += 1

    elif opcode == 'IDIV':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('/')
        instscount += 1

    elif opcode == 'ADD':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('+')
        instscount += 1

    elif opcode == 'SUB':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('-')
        instscount += 1

    elif opcode == 'WRITE':
        controlRightCountOfArguments(argumentcount, 1)
        stdoutprint(arg.text)
        instscount += 1

    elif opcode == 'EQ':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        compare('=')
        instscount += 1

    elif opcode == 'LT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        compare('<')
        instscount += 1

    elif opcode == 'GT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        compare('>')
        instscount += 1

    elif opcode == 'LABEL':
        controlRightCountOfArguments(argumentcount, 1)
        instscount += 1
        pass

    elif opcode == 'JUMP':
        controlRightCountOfArguments(argumentcount, 1)
        if arg.text not in labels.keys():
            Error.error_exit("NEEXISTUJUCE NAVESTI! {}\n".format(arg.text), 52)
        index = labels.get(arg.text) - 1
        instscount += 1

    elif opcode == 'JUMPIFNEQ':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        jumpifeq('!=')
        instscount += 1

    elif opcode == 'JUMPIFEQ':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        jumpifeq('=')
        instscount += 1

    elif opcode == 'CALL':
        controlRightCountOfArguments(argumentcount, 1)
        if arg.text not in labels.keys():
            Error.error_exit("NEEXISTUJUCE NAVESTI! {}\n".format(arg.text), 52)
        callStack.append(True)
        returnIndex = index
        callStackIndex.append(returnIndex)
        index = labels.get(arg.text) - 1
        instscount += 1

    elif opcode == 'PUSHS':
        controlRightCountOfArguments(argumentcount, 1)
        calculate.append("{}@{}".format(argtype, arg.text))
        stackPush()
        instscount += 1

    elif opcode == 'POPS':
        controlRightCountOfArguments(argumentcount, 1)
        calculate.append("{}@{}".format(argtype, arg.text))
        stackPop()
        instscount += 1

    elif opcode == 'AND':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        logical('=')
        instscount += 1

    elif opcode == 'OR':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        logical('or')
        instscount += 1

    elif opcode == 'NOT':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        logicalnot('not')
        instscount += 1

    elif opcode == 'STRI2INT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        stri2int()
        instscount += 1

    elif opcode == 'INT2CHAR':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        int2char()
        instscount += 1

    elif opcode == 'READ':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        readInstruction()
        instscount += 1

    elif opcode == 'CONCAT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        concat()
        instscount += 1

    elif opcode == 'STRLEN':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        strlen()
        instscount += 1

    elif opcode == 'GETCHAR':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        getchar()
        instscount += 1

    elif opcode == 'SETCHAR':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        setchar()
        instscount += 1

    elif opcode == 'EXIT':
        controlRightCountOfArguments(argumentcount, 1)
        calculate.append("{}@{}".format(argtype, arg.text))
        instscount += 1
        exitProg()

    elif opcode == 'MOVE':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        move()
        instscount += 1

    elif opcode == 'TYPE':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        typecheck()
        instscount += 1

    elif opcode == 'DPRINT':
        instscount += 1
        pass

    elif opcode == 'BREAK':
        instscount += 1
        pass

    elif opcode == 'JUMPIFEQS':
        controlRightCountOfArguments(argumentcount, 1)
        calculate.append("{}@{}".format(argtype, arg.text))
        jumpifeqS('=')
        instscount += 1

    elif opcode == 'JUMPIFNEQS':
        controlRightCountOfArguments(argumentcount, 1)
        calculate.append("{}@{}".format(argtype, arg.text))
        jumpifeqS('!=')
        instscount += 1

    else:
        Error.error_exit("UNKNOWN OPCODE!\n", 32)


def stri2intS():
    global calculate

    for m in range(0, 2):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    op3, type3 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not (re.match(r"{}".format(symbol_regex), calculate[0])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'string' or type3 != 'int':
        Error.error_exit("ZLY TYP PRE STRI2INT OPERACIU!\n", 53)

    if int(op3) >= len(op2) or int(op3) < 0:
        Error.error_exit("OP3 MIMO ROZSAHU STRLEN(op2)\n", 58)
    result = ord(op2[int(op3)])

    stack.append("int@{}".format(str(result).lower()))

    calculate.clear()


def int2charS():
    global calculate

    for m in range(0, 1):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    op2, type2 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if not (re.match(r"{}".format(symbol_regex), calculate[0])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if type2 != 'int':
        Error.error_exit("ZLY TYP PRE INT2CHAR OPERACIU!\n", 53)

    try:
        result = chr(int(op2))
    except:
        Error.error_exit("ZLA INT2CHAR OPERACIA\n", 58)

    stack.append("string@{}".format(str(result)))

    calculate.clear()


def logicalS(operator):
    global calculate

    for m in range(0, 2):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    if not (re.match(r"{}".format(symbol_regex), calculate[0])):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    op2, type2 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    op3, type3 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    calculate.clear()

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'bool' or type3 != 'bool':
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
    else:
        if operator == 'or':
            if op2 == 'true' or op3 == 'true':
                result = 'true'
            else:
                result = 'false'
        if operator == '=':
            if op2 == 'false' and op3 == 'false':
                result = 'false'
            else:
                result = ops["{}".format(operator)](op2, op3)

    stack.append("bool@{}".format(str(result).lower()))

    if type2 != type3:
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)


def logicalSnot(operator):
    global calculate
    for m in range(0, 1):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    if not (re.match(r"{}".format(symbol_regex), calculate[0])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    op2, type2 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if type2 != 'bool':
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
    else:
        if op2 == 'true':
            result = 'false'
        elif op2 == 'false':
            result = 'true'

    stack.append("bool@{}".format(str(result).lower()))
    calculate.clear()


def jumpifeqS(operator):
    global calculate
    global index

    if len(calculate) < 1:
        return

    for m in range(0, 2):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    result = False
    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if not re.match(r"^label@\S+$", calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if op1 not in labels.keys():
        Error.error_exit("NEEXISTUJUCE NAVESTI! {}\n".format(arg.text), 52)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    calculate.clear()
    if type2 != 'nil' and type3 != 'nil':
        if type2 != type3:
            Error.error_exit("ZLY TYP PRE JUMPIFEQ OPERACIU!\n", 53)
        if type2 == 'int' or type3 == 'int':
            if type2 != type3:
                Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
            result = ops["{}".format(operator)](int(op2), int(op3))
        else:
            result = ops["{}".format(operator)](op2, op3)
    else:
        if operator == '=':
            if type2 == 'nil' and type3 == 'nil':
                result = True
            else:
                result = False
        elif operator == '!=':
            if type2 == 'nil' and type3 == 'nil':
                result = False
            else:
                result = True

    if result:
        index = labels.get(op1) - 1


def compareS(operator):
    global calculate

    for m in range(0, 2):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not re.match(r"{}".format(symbol_regex), calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not re.match(r"{}".format(symbol_regex), calculate[1]):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    calculate.clear()

    if re.match(r"{}".format(varregex), op1):
        checkIfVarExists(localframe, tempframe, op1)
        if not (var.get(op1) or varLF.get(op1) or varTF.get(op1)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type1, op1 = variableIsGiven(op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if (type1 == 'nil' or type2 == 'nil') and operator != '=':
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
    if (type1 == 'int' or type2 == 'int') and operator != '=':
        if type1 != type2:
            Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
        result = ops["{}".format(operator)](int(op1), int(op2))
    else:
        result = ops["{}".format(operator)](op1, op2)


    result = 'bool@' + str(result).lower()
    stack.append(result)

    if type1 != type2:
        if (type1 == 'nil' or type2 == 'nil') and operator == '=':
            return
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)


def arithmeticsS(operator):
    global stack
    global calculate

    for m in range(0, 2):
        try:
            calculate.append(stack.pop())
        except:
            Error.error_exit("STACK JE PRAZDNY!\n", 56)

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]


    if not re.match(r"{}".format(symbol_regex), calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not re.match(r"{}".format(symbol_regex), calculate[1]):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op1):
        checkIfVarExists(localframe, tempframe, op1)
        if not (var.get(op1) or varLF.get(op1) or varTF.get(op1)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type1, op1 = variableIsGiven(op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if type1 != 'int' or type2 != 'int':
        Error.error_exit("ZLY TYP PRE ARITMETICKU OPERACIU!\n", 53)

    if operator == '/' and int(op2) == 0:
        Error.error_exit("ZERO DIVISION!\n", 57)
    result = ops["{}".format(operator)](int(op2), int(op1))
    result = 'int@' + str(result)
    stack.append(result)

    calculate.clear()


def setchar():
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    checkIfVarExists(localframe, tempframe, op1)
    type11, string = variableIsGiven(op1)

    if type11 != 'string':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'int' or type3 != 'string':
        Error.error_exit("ZLY TYP PRE SETCHAR OPERACIU!\n", 53)

    if int(op2) < 0 or int(op2) > len(string) - 1 or op3 == 'None':
        Error.error_exit("OP3 MIMO ROZSAHU SETCHAR(op1)\n", 58)

    if re.match(r"^(\\[0-9]{3})", op3[0:4]):
        toresult = op3[0:4]
        op3 = chr(int(toresult[1:]))

    lstring = list(string)
    lstring[int(op2)] = op3[0]
    result = "".join(lstring)

    if op1[0:2] == 'GF':
        var.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'LF':
        varLF.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'TF':
        varTF.update({op1: "string@{}".format(str(result))})

    calculate.clear()


def readInstruction():
    if len(calculate) < 2:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    checkIfVarExists(localframe,tempframe,op1)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    calculate.clear()

    if type2 != 'type':
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (op2 == 'int' or op2 == 'string' or op2 == 'bool'):
        if op1[0:2] == 'GF':
            var.update({op1: "nil@nil"})
        if op1[0:2] == 'LF':
            varLF.update({op1: "nil@nil"})
        if op1[0:2] == 'TF':
            varTF.update({op1: "nil@nil"})
        return
    try:
        loaded = input()
    except:
        if op1[0:2] == 'GF':
            var.update({op1: "nil@nil"})
        if op1[0:2] == 'LF':
            varLF.update({op1: "nil@nil"})
        if op1[0:2] == 'TF':
            varTF.update({op1: "nil@nil"})
        return

    if not loaded.lstrip('+-').isdigit() and op2 == 'int':
        if op1[0:2] == 'GF':
            var.update({op1: "nil@nil"})
        if op1[0:2] == 'LF':
            varLF.update({op1: "nil@nil"})
        if op1[0:2] == 'TF':
            varTF.update({op1: "nil@nil"})
        return
    elif op2 == 'bool':
        if loaded.lower() == 'true':
            result = 'bool@true'
        else:
            result = 'bool@false'
    else:
        result = f"{op2}@{loaded}"

    if op1[0:2] == 'GF':
        var.update({op1: f"{result}"})
    if op1[0:2] == 'LF':
        varLF.update({op1: f"{result}"})
    if op1[0:2] == 'TF':
        varTF.update({op1: f"{result}"})


def stackPop():
    global stack
    if len(calculate) < 1:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op1):
        checkIfVarExists(localframe, tempframe, op1)

    calculate.clear()
    try:
        result = stack.pop()
    except:
        Error.error_exit("STACK JE PRAZDNY!\n", 56)

    op2, type2 = result.split('@', 1)[1], result.split('@', 1)[0]

    if op1[0:2] == 'GF':
        var.update({op1: "{}@{}".format(type2, op2)})
    if op1[0:2] == 'LF':
        varLF.update({op1: "{}@{}".format(type2, op2)})
    if op1[0:2] == 'TF':
        varTF.update({op1: "{}@{}".format(type2, op2)})


def stackPush():
    global stack
    if len(calculate) < 1:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if not re.match(r"{}".format(symbol_regex), calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op1):
        checkIfVarExists(localframe, tempframe, op1)
        if not (var.get(op1) or varLF.get(op1) or varTF.get(op1)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type1, op1 = variableIsGiven(op1)

    calculate.clear()
    result = type1 + '@' + op1
    stack.append(result)


def jumpifeq(operator):
    if len(calculate) < 3:
        return

    global index
    result = False
    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if not re.match(r"^label@\S+$", calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if op1 not in labels.keys():
        Error.error_exit("NEEXISTUJUCE NAVESTI! {}\n".format(arg.text), 52)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    calculate.clear()
    if type2 != 'nil' and type3 != 'nil':
        if type2 != type3:
            Error.error_exit("ZLY TYP PRE JUMPIFEQ OPERACIU!\n", 53)
        if type2 == 'int' or type3 == 'int':
            if type2 != type3:
                Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
            result = ops["{}".format(operator)](int(op2), int(op3))
        else:
            result = ops["{}".format(operator)](op2, op3)
    else:
        if operator == '=':
            if type2 == 'nil' and type3 == 'nil':
                result = True
            else:
                result = False
        elif operator == '!=':
            if type2 == 'nil' and type3 == 'nil':
                result = False
            else:
                result = True

    if result:
        index = labels.get(op1) - 1


def exitProg():
    if len(calculate) < 1:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if not re.match(r"{}".format(symbol_regex), calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op1):
        checkIfVarExists(localframe, tempframe, op1)
        if not (var.get(op1) or varLF.get(op1) or varTF.get(op1)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type1, op1 = variableIsGiven(op1)

    if type1 != 'int':
        Error.error_exit("ZLY TYP PRE EXIT OPERACIU!\n", 53)

    calculate.clear()
    if int(op1) < 0 or int(op1) > 49:
        Error.error_exit("ZLY OPERAND PRE EXIT\n", 57)
    exit(int(op1))


def concat():
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'string' or type3 != 'string':
        Error.error_exit("ZLY TYP PRE CONCAT OPERACIU!\n", 53)

    if op2 == 'None':
        op2 = ''
    if op3 == 'None':
        op3 = ''
    result = op2 + op3

    if op1[0:2] == 'GF':
        var.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'LF':
        varLF.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'TF':
        varTF.update({op1: "string@{}".format(str(result))})

    calculate.clear()


def getchar():
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'string' or type3 != 'int':
        Error.error_exit("ZLY TYP PRE GETCHAR OPERACIU!\n", 53)

    if int(op3) >= len(op2) or int(op3) < 0:
        Error.error_exit("OP3 MIMO ROZSAHU STRLEN(op2)\n", 58)
    result = op2[int(op3)]

    if op1[0:2] == 'GF':
        var.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'LF':
        varLF.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'TF':
        varTF.update({op1: "string@{}".format(str(result))})

    calculate.clear()


def strlen():
    if len(calculate) < 2:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if type2 != 'string':
        Error.error_exit("ZLY TYP PRE STRLEN OPERACIU!\n", 53)

    result = len(op2)
    if op2 == 'None':
        result = 0

    if op1[0:2] == 'GF':
        var.update({op1: "int@{}".format(str(result).lower())})
    if op1[0:2] == 'LF':
        varLF.update({op1: "int@{}".format(str(result).lower())})
    if op1[0:2] == 'TF':
        varTF.update({op1: "int@{}".format(str(result).lower())})

    calculate.clear()


def int2char():
    if len(calculate) < 2:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if type2 != 'int':
        Error.error_exit("ZLY TYP PRE INT2CHAR OPERACIU!\n", 53)

    try:
        result = chr(int(op2))
    except:
        Error.error_exit("ZLA INT2CHAR OPERACIA\n", 58)

    if op1[0:2] == 'GF':
        var.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'LF':
        varLF.update({op1: "string@{}".format(str(result))})
    if op1[0:2] == 'TF':
        varTF.update({op1: "string@{}".format(str(result))})

    calculate.clear()


def stri2int():
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'string' or type3 != 'int':
        Error.error_exit("ZLY TYP PRE STRI2INT OPERACIU!\n", 53)

    if int(op3) >= len(op2) or int(op3) < 0:
        Error.error_exit("OP3 MIMO ROZSAHU STRLEN(op2)\n", 58)
    result = ord(op2[int(op3)])

    if op1[0:2] == 'GF':
        var.update({op1: "int@{}".format(str(result).lower())})
    if op1[0:2] == 'LF':
        varLF.update({op1: "int@{}".format(str(result).lower())})
    if op1[0:2] == 'TF':
        varTF.update({op1: "int@{}".format(str(result).lower())})

    calculate.clear()


def logicalnot(operator):
    if len(calculate) < 2:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if type2 != 'bool':
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
    else:
        if op2 == 'true':
            result = 'false'
        elif op2 == 'false':
            result = 'true'

    if op1[0:2] == 'GF':
        var.update({op1: "bool@{}".format(str(result).lower())})
    if op1[0:2] == 'LF':
        varLF.update({op1: "bool@{}".format(str(result).lower())})
    if op1[0:2] == 'TF':
        varTF.update({op1: "bool@{}".format(str(result).lower())})

    calculate.clear()


def logical(operator):
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if type2 != 'bool' or type3 != 'bool':
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
    else:
        if operator == 'or':
            if op2 == 'true' or op3 == 'true':
                result = 'true'
            else:
                result = 'false'
        if operator == '=':
            if op2 == 'false' and op3 == 'false':
                result = 'false'
            else:
                result = ops["{}".format(operator)](op2, op3)

    if op1[0:2] == 'GF':
        var.update({op1: "bool@{}".format(str(result).lower())})
    if op1[0:2] == 'LF':
        varLF.update({op1: "bool@{}".format(str(result).lower())})
    if op1[0:2] == 'TF':
        varTF.update({op1: "bool@{}".format(str(result).lower())})

    calculate.clear()
    if type2 != type3:
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)


def typecheck():
    if len(calculate) < 2:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            if not (op2 in var.keys() or op2 in varLF.keys() or op2 in varTF.keys()):
                Error.error_exit("NEEXISTUJUCA PREMENNA!\n", 54)
            if op2[0:2] == 'GF':
                ops = var.get(op2)
            if op2[0:2] == 'LF':
                ops = varLF.get(op2)
            if op2[0:2] == 'TF':
                ops = varTF.get(op2)
            if op2[0:2] == 'GF':
                type2 = var.get(op2).split('@', 1)[0]
            if op2[0:2] == 'LF':
                type2 = varLF.get(op2).split('@', 1)[0]
            if op2[0:2] == 'TF':
                type2 = varTF.get(op2).split('@', 1)[0]
            type2, op2 = type2, ops
        else:
            type2, op2 = variableIsGiven(op2)

    if op1[0:2] == 'GF':
        var.update({op1: "string@{}".format(type2)})
    if op1[0:2] == 'LF':
        varLF.update({op1: "string@{}".format(type2)})
    if op1[0:2] == 'TF':
        varTF.update({op1: "string@{}".format(type2)})

    calculate.clear()


def move():
    if len(calculate) < 2:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]

    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if op1[0:2] == 'GF':
        var.update({op1: "{}@{}".format(type2, op2)})
    if op1[0:2] == 'LF':
        varLF.update({op1: "{}@{}".format(type2, op2)})
    if op1[0:2] == 'TF':
        varTF.update({op1: "{}@{}".format(type2, op2)})
    calculate.clear()


def checkIfVarExists(localframe, tempframe, op1):
    if op1[0:2] == 'LF' or op1[0:2] == 'TF':
        if localframe and tempframe:
            if op1[0:2] != 'LF' and op1[0:2] != 'GF' and op1[0:2] != 'TF':
                Error.error_exit("NEEXISTUJUCI RAMEC! {}\n".format(operator), 55)
            if op1 not in var.keys() and op1 not in varLF.keys() and op1 not in varTF.keys():
                Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
            return
        elif localframe:
            if op1[0:2] != 'LF' and op1[0:2] != 'GF':
                Error.error_exit("NEEXISTUJUCI RAMEC! {}\n".format(operator), 55)
            if op1 not in var.keys() and op1 not in varLF.keys():
                Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
            return
        elif tempframe:
            if op1[0:2] != 'TF' and op1[0:2] != 'GF':
                Error.error_exit("NEEXISTUJUCI RAMEC! {}\n".format(operator), 55)
            if op1 not in var.keys() and op1 not in varTF.keys():
                Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
            return
        Error.error_exit("NEEXISTUJUCI RAMEC! {}\n".format(operator), 55)
    if op1 not in var.keys():
        Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
        return


def compare(operator):
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    if not (re.match(r"{}".format(symbol_regex), calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(symbol_regex), calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if op1 not in var.keys():
        checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
        checkIfVarExists(localframe, tempframe, op2)
        if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if (type2 == 'nil' or type3 == 'nil') and operator != '=':
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
    if (type2 == 'int' or type3 == 'int') and operator != '=':
        if type2 != type3:
            Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)
        result = ops["{}".format(operator)](int(op2), int(op3))
    else:
        result = ops["{}".format(operator)](op2, op3)

    if op1[0:2] == 'GF':
        var.update({op1: "bool@{}".format(str(result).lower())})
    if op1[0:2] == 'LF':
        varLF.update({op1: "bool@{}".format(str(result).lower())})
    if op1[0:2] == 'TF':
        varTF.update({op1: "bool@{}".format(str(result).lower())})

    calculate.clear()
    if type2 != type3:
        if (type2 == 'nil' or type3 == 'nil') and operator == '=':
            return
        Error.error_exit("ZLY TYP PRE COMPARE OPERACIU!\n", 53)


def stdoutprint(arg):
    if arg == 'nil@nil':
        myprint('')
        return
    if re.match(r"{}".format(varregex), arg):
        if arg not in var.keys():
            checkIfVarExists(localframe, tempframe, arg)
        if (arg[0:2] == 'GF'):
            testemptyvar = var.get(arg)
        if (arg[0:2] == 'LF'):
            testemptyvar = varLF.get(arg)
        if (arg[0:2] == 'TF'):
            testemptyvar = varTF.get(arg)
        if not testemptyvar:
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        if (arg[0:2] == 'GF'):
            myprint(var.get(arg).split('@', 1)[1])
        if (arg[0:2] == 'LF'):
            myprint(varLF.get(arg).split('@', 1)[1])
        if (arg[0:2] == 'TF'):
            myprint(varTF.get(arg).split('@', 1)[1])
        return
    myprint(arg)


def myprint(string):
    if string == 'nil':
        print('', end='')
        return
    print(string, end='')


def controlRightCountOfArguments(got, expected):
    if got != expected:
        Error.error_exit("ZLY POCET ARGUMENTOV V INSTRUCKII!\n", 32)
    return


def arithmetic(operator):
    if len(calculate) < 3:
        return

    op1, type1 = calculate[0].split('@', 1)[1], calculate[0].split('@', 1)[0]
    if type1 != 'var':
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)

    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(varregex), op2) or re.match(r"[+\-]?\d+", op2)):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(varregex), op3) or re.match(r"[+\-]?\d+", op3)):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if op1 not in var.keys():
         checkIfVarExists(localframe, tempframe, op1)

    if re.match(r"{}".format(varregex), op2):
         checkIfVarExists(localframe, tempframe, op2)
         if not (var.get(op2) or varLF.get(op2) or varTF.get(op2)):
             Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
         type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        checkIfVarExists(localframe, tempframe, op3)
        if not (var.get(op3) or varLF.get(op3) or varTF.get(op3)):
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
        type3, op3 = variableIsGiven(op3)

    if operator == '/' and int(op3) == 0:
        Error.error_exit("ZERO DIVISION!\n", 57)
    result = ops["{}".format(operator)](int(op2), int(op3))
    if op1[0:2] == 'GF':
        var.update({op1: "int@{}".format(str(result).lower())})
    if op1[0:2] == 'LF':
        varLF.update({op1: "int@{}".format(str(result).lower())})
    if op1[0:2] == 'TF':
        varTF.update({op1: "int@{}".format(str(result).lower())})

    calculate.clear()
    if type2 != 'int' or type3 != 'int':
        Error.error_exit("ZLY TYP PRE ARITMETICKU OPERACIU!\n", 53)


def variableIsGiven(op):
    if not (op in var.keys() or op in varLF.keys() or op in varTF.keys()):
        Error.error_exit("NEEXISTUJUCA PREMENNA!\n", 54)
    if op[0:2] == 'GF':
        ops = var.get(op)
    if op[0:2] == 'LF':
        ops = varLF.get(op)
    if op[0:2] == 'TF':
        ops = varTF.get(op)
    if ops == '':
        Error.error_exit("PREMENNA JE PRAZDNA!\n", 56)
    if op[0:2] == 'GF':
        types, op = var.get(op).split('@', 1)[0], var.get(op).split('@', 1)[1]
    if op[0:2] == 'LF':
        types, op = varLF.get(op).split('@', 1)[0], varLF.get(op).split('@', 1)[1]
    if op[0:2] == 'TF':
        types, op = varTF.get(op).split('@', 1)[0], varTF.get(op).split('@', 1)[1]

    return types, op


##########################################################################
##########################################################################
##########################################################################
##########################################################################
##########################################################################

parseArguments()

try:
    if inputfile.name == '<stdin>':
        pass
except:
    try:
        sys.stdin = open(inputfile, "r")
    except:
        Error.error_exit("SUBOR NEEXISTUJE!\n", 11)

try:
    root = ET.parse(sourcefile).getroot()
except:
    Error.error_exit("BAD XML!\n", 31)

actualorder = 0
argcontrol = []

try:
    if root.attrib["language"].upper() != 'IPPCODE20':
        Error.error_exit("BAD XML ATTRIBUTES FORMAT!\n", 32)
except:
    Error.error_exit("BAD XML ATTRIBUTES FORMAT!\n", 32)

for child in root:
    for checkkeys in child.attrib.keys():
        argcontrol.append(checkkeys)
    if len(argcontrol) < 2 or argcontrol[0] != 'order' or argcontrol[1] != 'opcode':
        Error.error_exit("BAD XML ATTRIBUTES FORMAT!\n", 32)
    argcontrol.clear()
    if child.tag != 'instruction':
        Error.error_exit("BAD XML INSTRUCTION FORMAT!\n", 32)
    try:
        gotorder = int(child.attrib["order"])
    except:
        Error.error_exit("BAD ORDER\n", 32)
    if int(actualorder) >= gotorder:
        Error.error_exit("BAD ORDER\n", 32)
    actualorder = child.attrib["order"]

instructions = root.findall("instruction")

for child in instructions:
    opcode = list(child.attrib.values())[1].upper()
    if opcode == 'LABEL':
        for arg in child:
            labelname = arg.text
        labelindex = index
        if labelname in labels.keys():
            Error.error_exit("REDEFINICIA NAVESTIA!\n", 52)
        labels.update({labelname: labelindex})
    index += 1

for child in instructions:
    for arg in child:
        for k in arg.attrib.values():
            if k == 'string':
                escaped = re.findall(r'(\\[0-9]{3})+', str(arg.text))
                for escape in escaped:
                    changed = chr(int(escape[1:]))
                    arg.text = arg.text.replace(escape, changed)

index = 0
i = 0

while i < len(instructions):
    child = instructions[index]
    parseXML(child)
    index += 1
    i = index

if isstats:
    file = open(outputfile, "w+")
    for stat in statistic:
        if stat == '--vars':
            file.write(str(varscount))
        elif stat == '--insts':
            file.write(str(instscount))
    file.close()
