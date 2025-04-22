import re

import pyparsing as pp
from pyparsing import ParseException

ALLOW_NAMED_VARIABLES = False
clear_terminal = "clear"
# os.system(clear_terminal)  # noqa: S605
# Define grammar here
vstart = pp.Literal("{{").suppress()
vend = pp.Literal("}}").suppress()
nonvar = pp.CharsNotIn("{}").suppress()
variable = (vstart + pp.Word(pp.alphanums + "_") + vend).set_name("variable")
# pos_var = vstart + pp.Word(pp.nums) + vend.set_name("positional_or_named_variable")
# valid_var = ""

# valid_var = named_var if ALLOW_NAMED_VARIABLES else pos_var
template_body = pp.OneOrMore(variable | nonvar)


print("******************  Start ******************")


def extract_vars(body):
    try:
        print("*********")

        # scan = template_body.scan_string(body)
        # print(f"Scan: {type(scan)}")

        parse_results = template_body.parse_string(body, parse_all=True)
        print(f"Parse results: {parse_results}")

        print("Parse Success")
    except ParseException as pe:
        print("Parse Failed")
        closing_braces = body.find("}}", pe.loc)
        if closing_braces > -1:
            var_name = body[pe.loc + 2 : closing_braces]
            print(f"Var name = {var_name}")
            if not re.match("^[a-zA-Z0-9_]+$", var_name):
                print(
                    "Variable name can only contain alphanumberic and underscore characters"
                )
        else:
            print(
                f"There was a problem parsing the variable starting at character {pe.loc}"
            )
    except Exception as e:
        print(f"Uncaught exception: {str(e)}")
    print("***********************************************************")


def main():
    print("String 1")
    extract_vars("foo {{1}} bar")
    print("String 2")
    extract_vars("Hi {{1_heresyour_thing}}")
    print("String 3")
    extract_vars("Hi {{1_heresyour_thing}")
    print("String 4")
    extract_vars("""
    Lots of text Lots of text {{1}}Lots of text Lots of text Lots of text{{2}}
    Lots of text Lots of text Lots of text Lots of text Lots of text Lots of {{no_good}}text Lots of text
    """)


# Check first variable

# If not integer, and named vars  not allowed, error

# If named vars allowed,
# if first var is integer 1, assume we are trying to use positional vars.abs
# check others as integer, and that they are in order.

# Throw error if anything other than int


main()
