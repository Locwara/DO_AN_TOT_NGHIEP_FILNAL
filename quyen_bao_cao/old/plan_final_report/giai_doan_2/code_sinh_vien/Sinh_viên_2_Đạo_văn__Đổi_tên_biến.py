def tinh_tong_so_nguyen_to(gioi_han):
    # Khởi tạo tổng
    tong_so = 0
    for n in range(2, gioi_han + 1):
        nguyen_to = True
        for j in range(2, int(n ** 0.5) + 1):
            if n % j == 0:
                nguyen_to = False
                break
        if nguyen_to == True:
            tong_so += n
    return tong_so