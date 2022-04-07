# astro-utils
 
Various utilities for processing astrophotography-related data. Required libraries include
pandas, astropy, PIL and plotly - the easiest way to ensure they're all present and correct
is to use the Anaconda Python distribution.

**index_plot.py**

Generate a plot of observed DSO image thumbnails on a log distance scale using simple rectangle packing.
Reads data from a csv file - see "Observing & Processing Information.csv" for an example.

See configuration section for details.

**3d index plot.ipynb**

Jupyter Notebook to produce interactive 3D plots of observed targets with linear and log distance scales.
Uses the same csv file as index_plot.py