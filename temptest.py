#%%
from tqdm import tqdm
import pylablib as pll
from pylablib.devices import DCAM # gives error if dll is not found. The dll is by default in system32 folder and automatically found. if not, then use code `pll.par["devices/dlls/dcamapi"] = "path/to/dlls"`
from pylablib.devices.DCAM.dcamapi4_lib import DCAMLibError
with DCAM.DCAMCamera() as cam:
    attrNames = [e for e in cam.attributes]
    dAttrTextSettings = dict()
    for attrName in tqdm(attrNames):
        intTextList = [] # to store (int, text), such as (1, "internal") for the attribute "trigger_source"
        attr = cam.ca[attrName]
        if attr.kind != "enum":
            dAttrTextSettings[attrName] = attr.kind
        else:
            for val in range(int(attr.min),int(attr.max)+1):
                try:
                    valText = attr.as_text(val)
                    intTextList.append((val, valText))
                except DCAMLibError:
                    intTextList.append((val, None))
            dAttrTextSettings[attrName] = intTextList
