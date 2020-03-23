import xml.etree.ElementTree as ET
import sys
import re
import operator

inputfile = sys.stdin
sourcefile = sys.stdin
varregex = "^(GF|LF|TF)@[a-zA-Z-_$&%*!?][a-zA-Z0-9-_$&%*!?]*$"
var = {}
calculate = []
ops = {"+": operator.add, "-": operator.sub, "/": operator.floordiv, "*": operator.mul}


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


def parseXML(child):
    args = []
    opcode = list(child.attrib.values())[1]
    argnumber = 1
    argumentcount = len(child)
    for arg in child:
        if arg.tag != 'arg{}'.format(argnumber):
            Error.error_exit("BAD XML!\n", 12)
        args.append(arg)
        functions(opcode, arg, argumentcount)
        # arg.tag == arg1, arg2 atd
        # arg.text == GF@a, 5, string, true, false....
        # arg.attrib.values()[0] == var, bool, string, int,...
        argnumber += 1


def functions(opcode, arg, argumentcount):
    argtype = list(arg.attrib.values())[0]

    if opcode == 'DEFVAR':
        if re.match(r"{}".format(varregex), arg.text):
            if (arg.text in var):
                Error.error_exit("REDEFINITION OF VARIABLE!\n", 52)
            var.update({arg.text: ""})
        else:
            Error.error_exit("WRONG FORMAT FOR DEFVAR!\n", 53)

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
        pass

    else:
        Error.error_exit("UNKNOWN OPCODE!\n", 53)


def stdoutprint(arg):
    # TODO NIL@NIL
    if re.match(r"{}".format(varregex), arg):
        if arg not in var.keys():
            Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
        myprint(var.get(arg).split('@', 1)[1])
        return

    myprint(arg)


def myprint(string):
    print(string, end='')


def controlRightCountOfArguments(got, expected):
    if got != expected:
        Error.error_exit("ZLY POCET ARGUMENTOV V INSTRUCKII!\n", 32)
    return


def arithmetic(operator):
    if len(calculate) < 3:
        return

    op1 = calculate[0].split('@', 1)[1]
    op2, type2 = calculate[1].split('@', 1)[1], calculate[1].split('@', 1)[0]
    op3, type3 = calculate[2].split('@', 1)[1], calculate[2].split('@', 1)[0]

    if not re.match(r"{}".format(varregex), op1):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 53)
    if not op1 in var.keys():
        Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
    if not (re.match(r"{}".format(varregex), op2) or re.match(r"[+\-]?\d+", op2)):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 53)
    if not (re.match(r"{}".format(varregex), op3) or re.match(r"[+\-]?\d+", op3)):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 53)

    if re.match(r"{}".format(varregex), op2):
        type2, op2 = variableIsGiven(op2)

    if re.match(r"{}".format(varregex), op3):
        type3, op3 = variableIsGiven(op3)

    if operator == '/' and int(op3) == 0:
        Error.error_exit("ZERO DIVISION!\n", 57)
    result = ops["{}".format(operator)](int(op2), int(op3))
    var.update({op1: "int@{}".format(result)})

    calculate.clear()
    if type2 != 'int' or type3 != 'int':
        Error.error_exit("ZLY TYP PRE ARITMETICKU OPERACIU!\n", 53)


def variableIsGiven(op):
    if not op in var.keys():
        Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 54)
    ops = var.get(op)
    if ops == '':
        Error.error_exit("PREMENNA JE PRAZDNA!\n", 56)
    types, op = var.get(op).split('@', 1)[0], var.get(op).split('@', 1)[1]
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

for child in root:
    parseXML(child)
