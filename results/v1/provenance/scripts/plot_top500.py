import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

df = pd.read_csv('data/top500_aggregated.csv', parse_dates=['Date'])
fig, ax = plt.subplots(figsize=(3.5, 2.25), dpi=300)

ax.plot(df['Date'], df['Total_Share_Percent'], 
        color='#1f77b4',  # Dark blue
        linewidth=1.5, 
        zorder=3)  

x_values = mdates.date2num(df['Date'])
ax.set_xlim(x_values.min(), x_values.max())

ax.fill_between(df['Date'], df['Total_Share_Percent'], 
                 color='#1f77b4', 
                 alpha=0.75,
                 zorder=2)  

ax.set_xlabel('Year', fontsize=8)
ax.set_ylabel('Systems with Accelerators (%)', fontsize=8)

ax.xaxis.set_major_locator(mdates.YearLocator(2))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))


ax.set_ylim(0, 60)
ax.set_yticks(range(0, 61, 10))
ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray', alpha=0.3, zorder=1)
ax.tick_params(axis='both', labelsize=6)
plt.tight_layout()

Path('figures').mkdir(exist_ok=True)
fig.savefig('figures/top500_accelerator_growth.pdf', format='pdf', bbox_inches='tight')
fig.savefig('figures/top500_accelerator_growth.png', format='png', dpi=300, bbox_inches='tight')
print("✅ Graph generation complete!")
print("   Outputs:")
print("   - figures/top500_accelerator_growth.pdf (vector)")
print("   - figures/top500_accelerator_growth.png (raster, 300 DPI)")
print(f"\n📈 Data range: {df['Total_Share_Percent'].min():.1f}% (Jun-06) to {df['Total_Share_Percent'].max():.1f}% (likely Nov-25)")
