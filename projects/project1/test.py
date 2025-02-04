def my_function(a: int, b: int) -> int:
    """
    my_function provides addition given two intengers provided by user

    input arg:
    a: int
    b: int
    return 
    c: int
    """
    c = a+b

    return c
var1 = int(input("enter an integer:"))
var2 = int(input("enter an integer:"))
var3 = my_function(var1, var2)
print("answer is ", var3)