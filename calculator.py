import sys

class Calculator:
    def add(self, x, y):
        return x + y

    def subtract(self, x, y):
        return x - y

    def multiply(self, x, y):
        return x * y

    def divide(self, x, y):
        if y == 0:
            return 'Error: Division by zero'
        return x / y

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: python calculator.py <operation> <num1> <num2>')
        sys.exit(1)

    operation = sys.argv[1]
    num1 = float(sys.argv[2])
    num2 = float(sys.argv[3])

    calculator = Calculator()

    if operation == 'add':
        print(calculator.add(num1, num2))
    elif operation == 'subtract':
        print(calculator.subtract(num1, num2))
    elif operation == 'multiply':
        print(calculator.multiply(num1, num2))
    elif operation == 'divide':
        print(calculator.divide(num1, num2))
    else:
        print('Unknown operation')