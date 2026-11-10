import os
import sys
from decimal import Context, Decimal
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.etree import ElementTree

# These are classes. Calling Addition(), for example, makes an Addition object.
from math_operations import Addition, Division, Multiplication, Subtraction

PAGE_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
CONTENT_TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}
XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>'


class CalculatorRequestHandler(BaseHTTPRequestHandler):
    """One handler object deals with a request. Python chooses do_GET or do_POST.

    BaseHTTPRequestHandler supplies headers, rfile and wfile, plus the methods
    used to send HTTP replies. We inherit these so we do not have to write HTTP parsing.
    """

    page_folder = PAGE_FOLDER

    def do_GET(self):
        # Send the HTML, JS and CSS directly. No frontend build is needed.
        # Keep only the file name so requests cannot reach files outside frontend.
        name = "index.html" if self.path == "/" else os.path.basename(self.path)
        file_path = os.path.join(self.page_folder, name)
        if not os.path.isfile(file_path):
            self._send(404, "application/xml", error_to_xml("Page not found: " + self.path))
            return

        with open(file_path, encoding="utf-8") as page_file:
            extension = os.path.splitext(file_path)[1]
            self._send(200, CONTENT_TYPES[extension], page_file.read())

    def do_POST(self):
        # rfile holds the incoming bytes. Content-Length tells us how many to read.
        # decode turns those bytes into the XML text sent by the browser.
        length = int(self.headers["Content-Length"])
        xml_text = self.rfile.read(length).decode("utf-8")

        # This is a list of Addition, Subtraction, Multiplication or Division objects
        # from math_operations.py. Each object already holds its inputs.
        # The list has one object per outer sum, so one request can have several answers.
        operations = read_xml(xml_text)
        # This prints object types and identities. get_inputs() can show an object's inputs.
        print(operations)
        try:
            answers = []
            for operation in operations:
                # operation is one object from that list. It inherits calculate()
                # from BaseOperation. That method uses this object's own _inputs.
                answers.append(operation.calculate())
            self._send(200, "application/xml", answers_to_xml(answers))
        except ZeroDivisionError:
            self._send(400, "application/xml", error_to_xml("Cannot divide by zero"))

    def _send(self, status_code, content_type, text):
        # Send the status, headers and text back to the browser.
        body = text.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def read_xml(xml):
    """Read XML and return a list of maths objects, one for each outer sum."""
    # The server passes text. Turn it into tags so we can read their attributes
    # and children. Recursive calls below already pass a tag, so skip this step.
    if isinstance(xml, (str, bytes)):
        xml = ElementTree.fromstring(xml)

    if "ID" in xml.attrib:
        # read_operation makes the object and fills its inputs. Put it in a list.
        # Its nested sums stay inside it; they are not separate answers.
        return [read_operation(xml)]

    # A tag without an ID is a wrapper, like <Maths>. Look inside each child.
    # Each call returns a list. extend adds its objects to our list in the same order.
    # We check ID instead of tag names so renamed XML tags still work (spec point 8).
    operations = []
    for child in xml:
        operations.extend(read_xml(child))
    return operations


def read_operation(tag):
    # The ID says which class to use. Addition() makes a new object, not a number.
    # Its inherited BaseOperation.__init__ runs automatically and creates _inputs = [].
    name = tag.attrib["ID"].strip().lower()
    if name in ("addition", "add", "plus", "sum", "+"):
        operation = Addition()
    elif name in ("subtraction", "subtract", "minus", "-"):
        operation = Subtraction()
    elif name in ("multiplication", "multiply", "times", "*", "x"):
        operation = Multiplication()
    elif name in ("division", "divide", "/"):
        operation = Division()
    else:
        raise KeyError(name)

    for child in tag:
        if "ID" in child.attrib:
            # Make the inner maths object first, including its own inputs.
            item = read_operation(child)
        else:
            # A number tag contains text. Fraction makes it an exact number.
            item = Fraction(child.text)
        # add_input is inherited from BaseOperation. It puts this number or inner
        # object into operation._inputs, ready for calculate() to use later.
        operation.add_input(item)
    return operation


def format_number(number):
    # Round only here, to 20 significant digits. Remove trailing zeros.
    number = Fraction(number)
    rounded = Context(prec=20).divide(Decimal(number.numerator), Decimal(number.denominator)).normalize()
    if rounded.adjusted() >= 20 or rounded.adjusted() < -20:
        return str(rounded)  # Very large or small answers use E notation.
    return format(rounded, "f")


def answers_to_xml(answers):
    result = ElementTree.Element("Result")
    for answer in answers:
        ElementTree.SubElement(result, "Answer").text = format_number(answer)
    return XML_HEADER + ElementTree.tostring(result, encoding="unicode")


def error_to_xml(message):
    error = ElementTree.Element("Error")
    error.text = message
    return XML_HEADER + ElementTree.tostring(error, encoding="unicode")


if __name__ == "__main__":
    # Run this only when starting server.py directly, not when tests import it.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    # localhost accepts requests from this computer. The with block closes the server when we finish.
    with ThreadingHTTPServer(("localhost", port), CalculatorRequestHandler) as server:
        print("Calculator is running. Open this in your browser: http://localhost:" + str(port))
        print("Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Stopping the server")
