import math

def check_prime(number):
    if number < 2: return False
    for i in range(2, math.isqrt(number) + 1):
        if number % i == 0:
            return False
    return True

def prime_sum(n):
    return sum(filter(check_prime, range(2, n + 1)))