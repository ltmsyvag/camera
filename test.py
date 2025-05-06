#%%
import matplotlib.pyplot as plt
import dearpygui.dearpygui as dpg

dpg.create_context()
colors = [dpg.get_colormap_color(dpg.mvPlotColormap_Viridis, i) for i in range(22)]
colors = [dpg.get_colormap_color(dpg.mvPlotColormap_Cool, i) for i in range(22)]
i=0
for color in colors:
    plt.plot(i, "o", color = color)
    i+=1
dpg.destroy_context()

# mylist = [[1,2,3], [4,5,6]]
# mylist2 = [[a*2, b*2, c*2] for a,b,c in mylist]
# print(mylist2)
# %%
