#%%
mylist = [0,1,2,3,4,5,6,7,8,9]
while (l := len(mylist)) > 5:
    print(l)
    mylist.pop()
len(mylist)