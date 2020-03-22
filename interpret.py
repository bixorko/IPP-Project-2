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
    for arg in child:
        if arg.tag != 'arg{}'.format(argnumber):
            Error.error_exit("BAD XML!\n", 12)
        args.append(arg)
        functions(opcode, arg)
        # arg.tag == arg1, arg2 atd
        # arg.text == GF@a, 5, string, true, false....
        # arg.attrib.values()[0] == var, bool, string, int,...
        argnumber += 1


def functions(opcode, arg):
    if opcode == 'DEFVAR':
        if re.match(r"{}".format(varregex), arg.text):
            var.update({arg.text: ""})
    if opcode == 'MUL':
        calculate.append(arg.text)
        arithmetic('*')
    if opcode == 'DIV':
        calculate.append(arg.text)
        arithmetic('/')
    if opcode == 'ADD':
        calculate.append(arg.text)
        arithmetic('+')
    if opcode == 'SUB':
        calculate.append(arg.text)
        arithmetic('-')


def arithmetic(operator):
    if len(calculate) < 3:
        return
    elif len(calculate) > 3:
        Error.error_exit("VELA ARGUMENTOV! MUL\n", 32)

    op2 = calculate[1]
    op3 = calculate[2]
    if not re.match(r"{}".format(varregex), calculate[0]):
        Error.error_exit("ZLY ARGUMENT 1! {}\n".format(operator), 32)
    if not calculate[0] in var.keys():
        Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 32)
    if not (re.match(r"{}".format(varregex), calculate[1]) or re.match(r"\d+", calculate[1])):
        Error.error_exit("ZLY ARGUMENT 2! {}\n".format(operator), 32)
    if not (re.match(r"{}".format(varregex), calculate[2]) or re.match(r"\d+", calculate[2])):
        Error.error_exit("ZLY ARGUMENT 3! {}\n".format(operator), 32)

    if re.match(r"{}".format(varregex), calculate[1]):
        if not calculate[1] in var.keys():
            Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 32)
        op2 = var.get(calculate[1])
    if re.match(r"{}".format(varregex), calculate[2]):
        if not calculate[2] in var.keys():
            Error.error_exit("NEEXISTUJUCA PREMENNA! {}\n".format(operator), 32)
        op3 = var.get(calculate[2])

    var.update({calculate[0]: ops["{}".format(operator)](int(op2), int(op3))})

    calculate.clear()


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

print(var)
