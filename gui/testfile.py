#%%
user_data = 1,2,3,4,5
d1, d2, *rest = user_data
print(rest)
d1 = 5
user_data = d1,d2,*rest
print(user_data)