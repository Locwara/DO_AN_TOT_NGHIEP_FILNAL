def calculate_prime_sum(limit):
    total_val = 0
    # Loop through all numbers
    for number in range(2, limit + 1):
        prime_flag = True
        for j in range(2, int(number ** 0.5) + 1):
            if number % j == 0:
                prime_flag = False
                break
        if prime_flag:
            total_val += number
    return total_val