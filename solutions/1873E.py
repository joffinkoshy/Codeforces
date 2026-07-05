import sys
input = sys.stdin.readline
t=int(input())
for _ in range(t):
    n,x=map(int,input().split())
    a=list(map(int,input().split()))

    high=max(a) + x
    low=min(a)
    H=low

    while low<=high:
        h=(low+high)//2
        ans=0
        for i in range(n):
            if h>=a[i]:
                ans+=h-a[i]

        if ans<=x:
            H=h
            low=h+1
        else:
            high=h-1

    print(H)
