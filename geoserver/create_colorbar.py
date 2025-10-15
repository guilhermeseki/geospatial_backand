import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def plot_vertical_colorbar():
    # Your original colors and values from GeoServer (starting from 1)
    colors = [
        '#50D0D0', '#00FFFF', '#00E080', '#00C000', '#CCE000',
        '#FFFF00', '#FFA000', '#FF0000', '#FF2080', '#F041FF',
        '#8020FF', '#4040FF', '#202080', '#202020', '#808080',
        '#E0E0E0', '#EED4BC', '#DAA675', '#A06C3C', '#663300'
    ]
    
    quantities = [
        1, 2.5, 5, 7.5, 10, 15, 20, 30, 40, 50,
        70, 100, 150, 200, 250, 300, 400, 500, 600, 750
    ]
    
    # Create a colormap from the discrete colors
    cmap = mcolors.ListedColormap(colors)
    
    # Create figure with vertical orientation - 1/4 width (0.75 instead of 3)
    fig, ax = plt.subplots(figsize=(1.2, 6))
    
    # Create boundaries for colorbar
    bounds = quantities
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    
    # Create vertical colorbar
    cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap),
                     cax=ax, orientation='vertical')
    
    # Set tick labels
    tick_positions = bounds
    tick_labels = [str(int(q)) if q.is_integer() else str(q) for q in bounds]
    cb.set_ticks(tick_positions)
    cb.set_ticklabels(tick_labels)
    
    # Style the colorbar - inverted (high values on top)
    cb.ax.invert_yaxis()
    cb.set_label('mm', fontsize=12, fontweight='bold', labelpad=5)
    cb.ax.tick_params(labelsize=12, rotation=0)
    
    plt.tight_layout()
    plt.savefig('precipitation_vertical_colorbar.png', dpi=300, bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    plot_vertical_colorbar()
