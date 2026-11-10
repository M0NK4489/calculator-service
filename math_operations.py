from abc import ABC, abstractmethod
from fractions import Fraction


class BaseOperation(ABC):
    """The parent class holds the code shared by all four operation classes.

    Each child inherits __init__, get_name, get_inputs, add_input and calculate.
    It supplies its own _name and combine. We share the other methods so the
    input handling and nested maths do not need to be written four times.
    """

    def __init__(self, inputs=None):
        # Python runs this when we make an object, such as Addition() or Division([8, 2]).
        # self means that new object. self._inputs creates a list stored on that object.
        # No inputs given? Start empty. Otherwise copy them so outside edits stay outside.
        self._inputs = list(inputs) if inputs is not None else []

    def get_name(self):
        # self is the child object, so _name comes from its class, e.g. Addition below.
        return self._name

    def get_inputs(self):
        # Return a copy so callers can inspect the inputs without changing our list.
        return list(self._inputs)

    def add_input(self, item):
        # read_operation() in server.py calls this while reading the XML.
        # item is a number or another maths object. Store it in the list __init__ made.
        self._inputs.append(item)

    def calculate(self):
        # In operation.calculate(), self is that operation object. Its _inputs was
        # created by __init__ and filled by add_input (or passed in when it was made).
        # numbers is a temporary list of answers. Keep the stored inputs unchanged.
        numbers = []
        for item in self._inputs:
            if isinstance(item, BaseOperation):
                # An Addition, Division, etc. also counts as a BaseOperation because
                # it inherits from it. Work out this inner object's inputs first.
                numbers.append(item.calculate())
            else:
                # Fractions keep the maths exact. Round only when sending the answer.
                numbers.append(Fraction(item))

        # Work left to right. [10, 3, 2] means (10 - 3) - 2 for subtraction.
        result = numbers[0]
        for number in numbers[1:]:
            # self is still the child object. For Addition, this calls Addition.combine;
            # for Division, it calls Division.combine. The shared loop stays the same.
            result = self.combine(result, number)
        return result

    # The parent does not know which arithmetic to do. This rule requires the child
    # to supply combine before an object can be made. It shows the interface in spec 1.
    @abstractmethod
    def combine(self, first, second):
        pass


class Addition(BaseOperation):
    _name = "Addition"

    def combine(self, first, second):
        return first + second


class Subtraction(BaseOperation):
    _name = "Subtraction"

    def combine(self, first, second):
        return first - second


class Multiplication(BaseOperation):
    _name = "Multiplication"

    def combine(self, first, second):
        return first * second


class Division(BaseOperation):
    _name = "Division"

    def combine(self, first, second):
        # Python raises ZeroDivisionError if second is zero. The server catches it.
        return first / second
