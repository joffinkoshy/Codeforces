import sys
input = sys.stdin.readline

t = int(input())

for _ in range(t):
    n = int(input())
    a = list(map(int, input().split()))

    ans = 0
    ok = True

    for i in range(n - 2, -1, -1):
        while a[i] >= a[i + 1]:
            if a[i] == 0:
                ok = False
                break
            a[i] //= 2
            ans += 1
        if not ok:
            break

    print(ans if ok else -1)