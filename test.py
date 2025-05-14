#%%
import re

pattern = r"2\d{3}$"

if re.match(pattern, "2000"):
    print("Match")