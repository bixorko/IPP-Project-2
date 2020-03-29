import xml.etree.ElementTree as ET
import sys
import re
import operator

inputfile = sys.stdin
sourcefile = sys.stdin
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
       "<": operator.lt, ">": operator.gt, "=": operator.eq}
index = 0
controlindex = 0


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

    if len(sys.argv) == 2:
        if sys.argv[1] == '--help':
            printHelp()
        elif re.match(r"^--input=\S+$", sys.argv[1]):
            inputfile = sys.argv[1].partition('=')[2]
        elif re.match(r"^--source=\S+$", sys.argv[1]):
            sourcefile = sys.argv[1].partition('=')[2]

    elif len(sys.argv) == 3:
        if re.match(r"^--input=\S+$", sys.argv[1]):
            inputfile = sys.argv[1].partition('=')[2]
        elif re.match(r"^--source=\S+$", sys.argv[1]):
            sourcefile = sys.argv[1].partition('=')[2]
        else:
            Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                             "PRE NAPOVEDU NAPISTE --help\n", 10)
            exit(10)
        if re.match(r"^--input=\S+$", sys.argv[2]):
            inputfile = sys.argv[2].partition('=')[2]
        elif re.match(r"^--source=\S+$", sys.argv[2]):
            sourcefile = sys.argv[2].partition('=')[2]
        else:
            Error.error_exit("ZLE ZADANE ARGUMENTY!\n"
                             "PRE NAPOVEDU NAPISTE --help\n", 10)

    else:
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
            Error.error_exit("BAD XML!\n", 12)

    args.remove(args.getchildren()[0])
    args.append(final[0])


def controlFlowForArgs2(args):
    final = []
    for arg in args:
        if arg.tag == 'arg1':
            final.insert(0, arg)
        elif arg.tag == 'arg2':
            final.insert(1, arg)
        else:
            Error.error_exit("BAD XML!\n", 12)

    args.remove(args.getchildren()[0])
    args.remove(args.getchildren()[0])
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
            Error.error_exit("BAD XML!\n", 12)

    args.remove(args.getchildren()[0])
    args.remove(args.getchildren()[0])
    args.remove(args.getchildren()[0])
    args.append(final[0])
    args.append(final[1])
    args.append(final[2])


def parseXML(child):
    global varTF
    global varLF
    global tempframe
    global localframe
    args = []
    opcode = list(child.attrib.values())[1]
    argumentcount = len(child)

    if opcode == 'CREATEFRAME':
        varTF = {}
        tempframe = True
        return

    if opcode == 'PUSHFRAME':
        if not tempframe:
            Error.error_exit("PRISTUP K NEDEFINOVANEMU RAMCI PUSHFRAME!\n", 55)
        varLF = varTF
        varTF = {}
        for item in varLF.keys():
            if re.match(r"TF@\S", item):
                string = item.split('@', 1)[1]
                varLF[f'LF@{string}'] = varLF.pop(f'TF@{string}')
        localframe = True
        tempframe = False
        return

    if opcode == 'POPFRAME':
        if not localframe:
            Error.error_exit("PRISTUP K NEDEFINOVANEMU RAMCI PUSHFRAME!\n", 55)
        varTF = varLF
        varLF = {}
        for item in varTF.keys():
            if re.match(r"LF@\S", item):
                string = item.split('@', 1)[1]
                varTF[f'TF@{string}'] = varTF.pop(f'LF@{string}')
        localframe = False
        tempframe = True
        return

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

    if opcode == 'DEFVAR':
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

    elif opcode == 'MUL':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('*')

    elif opcode == 'IDIV':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('/')

    elif opcode == 'ADD':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('+')

    elif opcode == 'SUB':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        arithmetic('-')

    elif opcode == 'WRITE':
        controlRightCountOfArguments(argumentcount, 1)
        stdoutprint(arg.text)

    elif opcode == 'EQ':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        compare('=')

    elif opcode == 'LT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        compare('<')

    elif opcode == 'GT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        compare('>')

    elif opcode == 'LABEL':
        pass

    elif opcode == 'JUMP':
        if arg.text not in labels.keys():
            Error.error_exit("NEEXISTUJUCE NAVESTI! {}\n".format(arg.text), 52)
        index = labels.get(arg.text) - 1

    elif opcode == 'JUMPIFNEQ':
        pass

    elif opcode == 'JUMPIFEQ':
        pass

    elif opcode == 'CALL':
        pass

    elif opcode == 'RETURN':
        pass

    elif opcode == 'PUSHS':
        pass

    elif opcode == 'POPS':
        pass

    elif opcode == 'AND':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        logical('=')

    elif opcode == 'OR':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        logical('or')

    elif opcode == 'NOT':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        logicalnot('not')

    elif opcode == 'STRI2INT':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        stri2int()

    elif opcode == 'INT2CHAR':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        int2char()

    elif opcode == 'READ':
        pass

    elif opcode == 'CONCAT':
        pass

    elif opcode == 'STRLEN':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        strlen()

    elif opcode == 'GETCHAR':
        controlRightCountOfArguments(argumentcount, 3)
        calculate.append("{}@{}".format(argtype, arg.text))
        getchar()

    elif opcode == 'SETCHAR':
        pass

    elif opcode == 'EXIT':
        pass

    elif opcode == 'MOVE':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        move()

    elif opcode == 'TYPE':
        controlRightCountOfArguments(argumentcount, 2)
        calculate.append("{}@{}".format(argtype, arg.text))
        typecheck()

    elif opcode == 'DPRINT':
        pass

    elif opcode == 'BREAK':
        pass

    else:
        Error.error_exit("UNKNOWN OPCODE!\n", 53)


def concat():
    pass


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
            Error.error_exit("PREMENNA JE PRAZDNA! {}\n".format(operator), 56)
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
        if localframe:
            if op1[0:2] != 'LF' and op1[0:2] != 'GF':
                Error.error_exit("NEEXISTUJUCI RAMEC! {}\n".format(operator), 55)
            if op1 not in var.keys() and op1 not in varLF.keys():
                Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
            return
        if tempframe:
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
    root = ET.parse(sourcefile).getroot()
except:
    Error.error_exit("BAD XML!\n", 12)

instructions = root.findall("instruction")

for child in instructions:
    opcode = list(child.attrib.values())[1]
    if opcode == 'LABEL':
        for arg in child:
            labelname = arg.text
        labelindex = index
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
