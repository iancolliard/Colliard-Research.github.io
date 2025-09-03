import matplotlib.pyplot as plt
import pandas as pd

# Load periodic table data
url = "https://raw.githubusercontent.com/Bowserinator/Periodic-Table-JSON/master/PeriodicTableCSV.csv"
elements = pd.read_csv(url)

# Normalize column names to lowercase
elements.columns = elements.columns.str.lower()

# === EDIT THIS LIST WITH YOUR ELEMENTS ===
my_elements = {"Cm", "Eu", "La", "W", "Cs", "Na", "Ce", "Pr", "Nd", "Sm", "Gd",
               "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Th", "U", "Np", "Pu",
               "Am", "Cf", "Li", "K","Rb", "Ca", "Sr", "Ba", "Y", "V", "Nb",
               "Fe", "Co", "Ni", "Cu", "Zn", "Cd", "Ag", "Re", "Tl", "B", "C",
               "N", "O", "F", "Cl", "Br", "I", "S", "Se", "P", "Si", "Ga",
               "Ge", "Sn", "Pb", "Cr", "Mn", "Mo", "Bi", "Ta", "Zr", "Hf", 
               "H", "Ra"}

# Create figure
fig, ax = plt.subplots(figsize=(15,8))

for _, row in elements.iterrows():
    color = "lightblue" if row["symbol"] in my_elements else "none"
    
    ax.add_patch(plt.Rectangle(
        (row["xpos"], -row["ypos"]), 1, 1,
        edgecolor="black", facecolor=color, linewidth=3
    ))
    
    ax.text(row["xpos"]+0.5, -row["ypos"]+0.5,
            row["symbol"],
            ha="center", va="center", fontsize=16, weight="bold")

# Transparent background
fig.patch.set_alpha(0.0)
ax.set_facecolor("none")

ax.set_xlim(0, 19)
ax.set_ylim(-10, 0)
ax.axis("off")

plt.title("Elements I have crystallized", fontsize=20, weight="bold")

# Save with transparent background
plt.savefig("periodic_table.png", dpi=300, transparent=True)
plt.show()

