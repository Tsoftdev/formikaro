import re
import matplotlib.colors


def hexToHsl(hx):

    if not hx.find('#') != -1:
        hx = '#' + hx

    hls = matplotlib.colors.to_rgba(hx)
    return hls

name = 'Johannes ärnaz Josef Hermann Reschl'

def get_initials(fullname):
  xs = (fullname)
  name_list = xs.split()

  initials = ""

  for name in name_list:  # go through each name
    initials += name[0].upper()  # append the initial

  return initials

#init = re.search(name, "(\b[a-zA-Z])[a-zA-Z]* ?")
init = get_initials(name)
print("name: ", init)