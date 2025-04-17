import pyparsing as pp
from pyparsing import ParseException

ALLOW_NAMED_VARIABLES = False

# Define grammar here
vstart = pp.Literal("{{").suppress()
vend = pp.Literal("}}").suppress()
nonvar = pp.CharsNotIn("{}").suppress()
pos_var = (
    vstart
    + pp.Word(pp.alphanums)
    + "_"
    + vend.set_name("positional variable").set_debug()
)
named_var = (
    vstart
    + pp.Word(pp.nums)
    + vend.set_name("positional or named variable").set_debug()
)
valid_var = ""
if ALLOW_NAMED_VARIABLES:
    print("Allowing named and positional variables")
    valid_var = named_var
else:
    print("Only allowing positional variables. Named variables not allowed")
    valid_var = pos_var

template_body = pp.OneOrMore(named_var | nonvar)


print("******************  Start ******************")


def extract_vars(body):
    try:
        template_body.parse_string(body, parse_all=True)
        print(body)
        print("Parse Success")
    except ParseException as pe:
        print(
            f"There was a problem parsing the variable starting at character {pe.loc}"
        )
        closing_braces = body.find("}}", pe.loc)
        var_name = body[pe.loc + 2 : closing_braces]
        print(f"Var name = {var_name}")
    except Exception:
        # print(str(e))
        print("***********************************************************")


def main():
    multiline_body = """
    Lots of text Lots of text {{1}}Lots of text Lots of text Lots of text{{2}}
    Lots of text Lots of text Lots of text Lots of text Lots of text Lots of {{no_good}}text Lots of text
    """

    extract_vars("foo {{1} bar")

    extract_vars("Hi {{1}}, here's your {{thing}}")

    extract_vars(multiline_body)


# Check first variable

# If not integer, and named vars  not allowed, error

# If named vars allowed,
# if first var is integer 1, assume we are trying to use positional vars.abs
# check others as integer, and that they are in order.
# Throw error if anything other than int


main()
