def get_sum_of_primes(n):
    primes = []
    for i in range(2, n + 1):
        primes.append(i)
    
    p = 2
    while (p * p <= n):
        if p in primes:
            for i in range(p * p, n + 1, p):
                if i in primes:
                    primes.remove(i)
        p += 1
    return sum(primes)