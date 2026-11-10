import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from fractions import Fraction
from http.server import ThreadingHTTPServer

from math_operations import Addition, BaseOperation, Division, Multiplication, Subtraction
from server import CalculatorRequestHandler, answers_to_xml, error_to_xml, format_number, read_xml



# Sample inputs shared by the tests. All of them work out 2 + 3 + (4 x 5) = 25

SAMPLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Maths><Operation ID="Plus"><Value>2</Value><Value>3</Value>'
    '<Operation ID="Multiplication"><Value>4</Value><Value>5</Value></Operation>'
    '</Operation></Maths>'
)

# The spec's second sample, with different tag names
MY_MATHS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<MyMaths><MyOperation ID="Plus"><Value>2</Value><Value>3</Value>'
    '<MyOperation ID="Multiplication"><Value>4</Value><Value>5</Value></MyOperation>'
    '</MyOperation></MyMaths>'
)

# Every name changed, including the number tags and the operation names
DIFFERENT_NAMES_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Request><Sum ID="Add"><Number>2</Number><Number>3</Number>'
    '<Sum ID="Times"><Number>4</Number><Number>5</Number></Sum>'
    '</Sum></Request>'
)

EXPECTED_ANSWER_XML = '<?xml version="1.0" encoding="UTF-8"?><Result><Answer>25</Answer></Result>'



class TestAddition(unittest.TestCase):

    def test_adds_two_numbers(self):
        self.assertEqual(Addition([2, 3]).calculate(), 5)

    def test_adds_many_numbers(self):
        self.assertEqual(Addition([1, 2, 3, 4]).calculate(), 10)

    def test_adds_negative_and_decimal_numbers(self):
        self.assertEqual(Addition([-1.5, 4]).calculate(), 2.5)


class TestSubtraction(unittest.TestCase):

    def test_subtracts_two_numbers(self):
        self.assertEqual(Subtraction([10, 4]).calculate(), 6)

    def test_subtracts_from_left_to_right(self):
        self.assertEqual(Subtraction([10, 3, 2]).calculate(), 5)

    def test_can_give_a_negative_answer(self):
        self.assertEqual(Subtraction([3, 10]).calculate(), -7)


class TestMultiplication(unittest.TestCase):

    def test_multiplies_two_numbers(self):
        self.assertEqual(Multiplication([4, 5]).calculate(), 20)

    def test_multiplies_many_numbers(self):
        self.assertEqual(Multiplication([2, 3, 4]).calculate(), 24)

    def test_multiplying_by_zero_gives_zero(self):
        self.assertEqual(Multiplication([7, 0]).calculate(), 0)


class TestDivision(unittest.TestCase):

    def test_divides_two_numbers(self):
        self.assertEqual(Division([20, 4]).calculate(), 5)

    def test_divides_from_left_to_right(self):
        self.assertEqual(Division([100, 5, 2]).calculate(), 10)

    def test_can_give_a_decimal_answer(self):
        self.assertEqual(Division([1, 4]).calculate(), 0.25)

    def test_zero_divided_by_a_number_is_zero(self):
        self.assertEqual(Division([0, 5]).calculate(), 0)

    def test_dividing_by_zero_raises_an_error(self):
        with self.assertRaises(ZeroDivisionError):
            Division([4, 0]).calculate()

    def test_dividing_by_zero_later_in_the_list_raises_an_error(self):
        with self.assertRaises(ZeroDivisionError):
            Division([100, 5, 0]).calculate()


class TestNestedOperations(unittest.TestCase):

    def test_example_from_the_spec(self):
        # 2 + 3 + (4 x 5) = 25
        plus = Addition([2, 3, Multiplication([4, 5])])
        self.assertEqual(plus.calculate(), 25)

    def test_deeply_nested_operations(self):
        # 1 + (2 x (10 - (8 / 2))) = 13
        plus = Addition([1, Multiplication([2, Subtraction([10, Division([8, 2])])])])
        self.assertEqual(plus.calculate(), 13)

    def test_nested_operation_keeps_its_place_in_the_order(self):
        # (10 + 5) - 3 = 12, not 3 - 15
        subtract = Subtraction([Addition([10, 5]), 3])
        self.assertEqual(subtract.calculate(), 12)

    def test_operation_made_only_of_nested_operations(self):
        # (2 x 3) + (4 x 5) = 26
        plus = Addition([Multiplication([2, 3]), Multiplication([4, 5])])
        self.assertEqual(plus.calculate(), 26)

    def test_divide_by_zero_inside_a_nested_operation_raises_an_error(self):
        with self.assertRaises(ZeroDivisionError):
            Addition([1, Division([4, 0])]).calculate()


class TestInputs(unittest.TestCase):

    def test_starts_with_no_inputs(self):
        self.assertEqual(Addition().get_inputs(), [])

    def test_add_input_puts_it_on_the_end(self):
        operation = Addition([3])
        operation.add_input(4)
        self.assertEqual(operation.get_inputs(), [3, 4])

    def test_changing_the_list_from_get_inputs_does_not_change_the_operation(self):
        operation = Addition([3, 4])
        inputs = operation.get_inputs()
        inputs.append(100)
        self.assertEqual(operation.get_inputs(), [3, 4])

    def test_two_operations_do_not_share_the_same_inputs(self):
        first = Addition()
        second = Addition()
        first.add_input(1)
        self.assertEqual(second.get_inputs(), [])

    def test_changing_the_original_list_does_not_change_the_operation(self):
        inputs = [2, 3]
        operation = Addition(inputs)
        inputs.append(100)
        self.assertEqual(operation.calculate(), 5)


class TestAllOperations(unittest.TestCase):

    def setUp(self):
        self.all_classes = [Addition, Subtraction, Multiplication, Division]

    def test_every_operation_uses_the_interface(self):
        for operation_class in self.all_classes:
            operation = operation_class()
            self.assertIsInstance(operation, BaseOperation)

    def test_every_operation_has_the_right_name(self):
        self.assertEqual(Addition().get_name(), "Addition")
        self.assertEqual(Subtraction().get_name(), "Subtraction")
        self.assertEqual(Multiplication().get_name(), "Multiplication")
        self.assertEqual(Division().get_name(), "Division")

    def test_one_input_is_returned_unchanged(self):
        for operation_class in self.all_classes:
            self.assertEqual(operation_class([7]).calculate(), 7)

    def test_the_interface_cannot_be_created_on_its_own(self):
        with self.assertRaises(TypeError):
            BaseOperation()

    def test_a_child_must_supply_combine(self):
        class MissingMaths(BaseOperation):
            pass

        with self.assertRaises(TypeError):
            MissingMaths()


class TestOperationNames(unittest.TestCase):

    def test_creates_each_operation_from_its_different_names(self):
        names_to_check = {
            "Addition": Addition,
            "Plus": Addition,
            "Add": Addition,
            "Sum": Addition,
            "+": Addition,
            "Subtraction": Subtraction,
            "Subtract": Subtraction,
            "Minus": Subtraction,
            "-": Subtraction,
            "Multiplication": Multiplication,
            "Multiply": Multiplication,
            "Times": Multiplication,
            "*": Multiplication,
            "x": Multiplication,
            "Division": Division,
            "Divide": Division,
            "/": Division,
        }

        for name in names_to_check:
            expected_class = names_to_check[name]
            operation = read_xml('<Operation ID="' + name + '"/>')[0]
            self.assertIsInstance(operation, expected_class, "Failed for: " + name)

    def test_upper_or_lower_case_does_not_matter(self):
        self.assertIsInstance(read_xml('<Operation ID="PLUS"/>')[0], Addition)
        self.assertIsInstance(read_xml('<Operation ID="plus"/>')[0], Addition)

    def test_spaces_around_the_name_are_ignored(self):
        self.assertIsInstance(read_xml('<Operation ID="  Plus  "/>')[0], Addition)

    def test_creates_a_new_operation_every_time(self):
        first = read_xml('<Operation ID="Plus"/>')[0]
        second = read_xml('<Operation ID="Plus"/>')[0]
        self.assertIsNot(first, second)


def check_sample_was_read_correctly(test, operations):
    """Every sample should become Addition([2, 3, Multiplication([4, 5])])."""
    test.assertEqual(len(operations), 1)
    plus = operations[0]
    test.assertIsInstance(plus, Addition)

    inputs = plus.get_inputs()
    test.assertEqual(len(inputs), 3)
    test.assertEqual(inputs[0], 2)
    test.assertEqual(inputs[1], 3)

    multiply = inputs[2]
    test.assertIsInstance(multiply, Multiplication)
    test.assertEqual(multiply.get_inputs(), [4, 5])


class TestReadXml(unittest.TestCase):

    def test_reads_the_sample_xml(self):
        check_sample_was_read_correctly(self, read_xml(SAMPLE_XML))

    def test_reads_xml_with_different_tag_names(self):
        check_sample_was_read_correctly(self, read_xml(MY_MATHS_XML))

    def test_reads_xml_where_every_name_is_different(self):
        check_sample_was_read_correctly(self, read_xml(DIFFERENT_NAMES_XML))

    def test_reads_xml_with_no_outer_tag(self):
        operations = read_xml('<Operation ID="Minus"><Value>9</Value><Value>4</Value></Operation>')
        self.assertIsInstance(operations[0], Subtraction)
        self.assertEqual(operations[0].get_inputs(), [9, 4])

    def test_reads_several_operations(self):
        xml_text = (
            '<Maths>'
            '<Operation ID="Plus"><Value>1</Value><Value>2</Value></Operation>'
            '<Operation ID="Times"><Value>3</Value><Value>4</Value></Operation>'
            '</Maths>'
        )
        operations = read_xml(xml_text)
        self.assertEqual(len(operations), 2)
        self.assertIsInstance(operations[0], Addition)
        self.assertIsInstance(operations[1], Multiplication)

    def test_extra_wrappers_do_not_change_the_answer(self):
        operations = read_xml("<Request><Body>" + MY_MATHS_XML.split("?>")[1] + "</Body></Request>")
        self.assertEqual([operation.calculate() for operation in operations], [25])

    def test_keeps_values_in_the_same_order_as_the_xml(self):
        xml_text = (
            '<Operation ID="Minus">'
            '<Operation ID="Plus"><Value>10</Value><Value>5</Value></Operation>'
            '<Value>3</Value>'
            '</Operation>'
        )
        inputs = read_xml(xml_text)[0].get_inputs()
        self.assertIsInstance(inputs[0], Addition)
        self.assertEqual(inputs[1], 3)

    def test_reads_decimal_numbers_exactly(self):
        inputs = read_xml('<Operation ID="Plus"><Value>0.1</Value><Value>2.5</Value></Operation>')[0].get_inputs()
        self.assertEqual(inputs, [Fraction(1, 10), Fraction(5, 2)])


class TestWritingXml(unittest.TestCase):

    def test_whole_numbers_have_no_decimal_point(self):
        self.assertEqual(format_number(25.0), "25")
        self.assertEqual(format_number(-3.0), "-3")
        self.assertEqual(format_number(7), "7")

    def test_decimal_numbers_keep_their_decimal_point(self):
        self.assertEqual(format_number(2.5), "2.5")
        self.assertEqual(format_number(0.25), "0.25")

    def test_answers_are_rounded_to_20_significant_digits(self):
        self.assertEqual(format_number(Fraction(1, 3)), "0.33333333333333333333")

    def test_scientific_notation_starts_at_the_same_limits(self):
        cases = {
            "1e19": "10000000000000000000", "1e20": "1E+20",
            "1e-20": "0.00000000000000000001", "1e-21": "1E-21",
        }
        for number, expected in cases.items():
            self.assertEqual(format_number(Fraction(number)), expected)

    def test_writes_one_answer(self):
        self.assertEqual(
            answers_to_xml([25]),
            '<?xml version="1.0" encoding="UTF-8"?><Result><Answer>25</Answer></Result>',
        )

    def test_writes_several_answers(self):
        self.assertEqual(
            answers_to_xml([3, 2.5]),
            '<?xml version="1.0" encoding="UTF-8"?><Result><Answer>3</Answer><Answer>2.5</Answer></Result>',
        )

    def test_writes_an_error(self):
        self.assertEqual(
            error_to_xml("Something broke"),
            '<?xml version="1.0" encoding="UTF-8"?><Error>Something broke</Error>',
        )

    def test_error_text_is_escaped_as_xml(self):
        self.assertIn("<Error>A &amp; B &lt; C</Error>", error_to_xml("A & B < C"))


class QuietRequestHandler(CalculatorRequestHandler):
    """The real handler, without a log line for every request."""

    def log_message(self, format, *args):
        pass


def write_file(path, text):
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


class TestServer(unittest.TestCase):
    """Starts a real server on a free port and sends real HTTP requests to it."""

    @classmethod
    def setUpClass(cls):
        # A small pretend web page keeps these HTTP tests independent of the real UI.
        cls.temp_folder = tempfile.TemporaryDirectory()
        page_folder = os.path.join(cls.temp_folder.name, "page")
        os.makedirs(page_folder)
        write_file(os.path.join(page_folder, "index.html"), "<title>Calculator</title>")
        write_file(os.path.join(page_folder, "app.js"), "console.log('hello')")
        write_file(os.path.join(page_folder, "styles.css"), "body { color: red; }")

        # A file next to the page folder, which the server must never send
        write_file(os.path.join(cls.temp_folder.name, "secret.html"), "Top secret text")

        QuietRequestHandler.page_folder = page_folder

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietRequestHandler)
        cls.url = "http://127.0.0.1:" + str(cls.server.server_address[1])

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()
        cls.temp_folder.cleanup()

    def send_post(self, body_text):
        request = urllib.request.Request(self.url, data=body_text.encode("utf-8"), method="POST")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            # urllib raises on 400/500 codes, but we still want the response
            body = error.read().decode("utf-8")
            error.close()
            return error.code, body

    def send_get(self, path):
        try:
            with urllib.request.urlopen(self.url + path) as response:
                return response.status, response.headers["Content-Type"], response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8")
            error.close()
            return error.code, error.headers["Content-Type"], body

    def test_post_xml_gives_the_answer_as_xml(self):
        status, body = self.send_post(SAMPLE_XML)
        self.assertEqual(status, 200)
        self.assertEqual(body, EXPECTED_ANSWER_XML)

    def test_post_xml_with_different_names_gives_the_answer(self):
        status, body = self.send_post(MY_MATHS_XML)
        self.assertEqual(status, 200)
        self.assertEqual(body, EXPECTED_ANSWER_XML)

    def test_post_xml_where_every_name_is_different_gives_the_answer(self):
        status, body = self.send_post(DIFFERENT_NAMES_XML)
        self.assertEqual(status, 200)
        self.assertEqual(body, EXPECTED_ANSWER_XML)

    def test_post_several_operations_gives_several_answers(self):
        xml_text = (
            '<Maths>'
            '<Operation ID="Plus"><Value>1</Value><Value>2</Value></Operation>'
            '<Operation ID="Divide"><Value>5</Value><Value>2</Value></Operation>'
            '</Maths>'
        )
        status, body = self.send_post(xml_text)
        self.assertEqual(status, 200)
        self.assertIn("<Answer>3</Answer><Answer>2.5</Answer>", body)

    def test_post_xml_with_operations_inside_operations_gives_the_answer(self):
        # This is the XML the web page sends for ((2 + 3) × 4) − 1 = 19
        xml_text = (
            '<Maths>'
            '<Operation ID="Minus">'
            '<Operation ID="Multiplication">'
            '<Operation ID="Plus"><Value>2</Value><Value>3</Value></Operation>'
            '<Value>4</Value>'
            '</Operation>'
            '<Value>1</Value>'
            '</Operation>'
            '</Maths>'
        )
        status, body = self.send_post(xml_text)
        self.assertEqual(status, 200)
        self.assertIn("<Answer>19</Answer>", body)

    def test_answers_are_exact(self):
        # Normal computer numbers (floats) would give 0.30000000000000004 for 0.1 + 0.2
        sums = {
            '<Operation ID="Plus"><Value>0.1</Value><Value>0.2</Value></Operation>': "0.3",
            '<Operation ID="Times"><Value>1.1</Value><Value>3</Value></Operation>': "3.3",
            '<Operation ID="Minus"><Value>0.3</Value><Value>0.1</Value></Operation>': "0.2",
            '<Operation ID="Minus"><Value>0.3</Value><Value>0.1</Value><Value>0.2</Value></Operation>': "0",
            '<Operation ID="Times"><Value>123456789</Value><Value>987654321</Value></Operation>': "121932631112635269",
            '<Operation ID="Divide"><Value>1</Value><Value>3</Value></Operation>': "0.33333333333333333333",
            '<Operation ID="Times"><Operation ID="Divide"><Value>1</Value><Value>3</Value></Operation><Value>3</Value></Operation>': "1",
            '<Operation ID="Minus"><Operation ID="Times"><Operation ID="Divide"><Value>1</Value><Value>3</Value></Operation><Value>3</Value></Operation><Value>1</Value></Operation>': "0",
            '<Operation ID="Times"><Value>1e308</Value><Value>10</Value></Operation>': "1E+309",
            '<Operation ID="Times"><Value>0</Value><Value>-1</Value></Operation>': "0",
        }
        for xml_text, expected in sums.items():
            with self.subTest(xml_text):
                status, body = self.send_post(xml_text)
                self.assertEqual(status, 200)
                self.assertIn("<Answer>" + expected + "</Answer>", body)

    def test_post_divide_by_zero_gives_a_400_error(self):
        status, body = self.send_post('<Operation ID="Divide"><Value>4</Value><Value>0</Value></Operation>')
        self.assertEqual(status, 400)
        self.assertIn("<Error>", body)
        self.assertIn("zero", body)

    def test_get_gives_the_web_page(self):
        status, content_type, body = self.send_get("/")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("<title>Calculator</title>", body)

    def test_get_gives_the_javascript_for_the_page(self):
        status, content_type, body = self.send_get("/app.js")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/javascript; charset=utf-8")
        self.assertIn("hello", body)

    def test_get_gives_the_styles_for_the_page(self):
        status, content_type, body = self.send_get("/styles.css")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/css; charset=utf-8")
        self.assertIn("color: red", body)

    def test_get_an_unknown_page_gives_a_404_error(self):
        status, content_type, body = self.send_get("/not-a-page")
        self.assertEqual(status, 404)

    def test_get_cannot_read_files_outside_the_page_folder(self):
        status, content_type, body = self.send_get("/../secret.html")
        self.assertEqual(status, 404)
        self.assertNotIn("Top secret text", body)


if __name__ == "__main__":
    unittest.main()
