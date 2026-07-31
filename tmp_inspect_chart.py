import pandas as pd
from lightweight_charts import JupyterChart

chart = JupyterChart(width=800, height=400)
df = pd.DataFrame({'time':['2024-01-01','2024-01-02','2024-01-03'], 'value':[1,2,3]})
line = chart.create_line(name='Test', color='#ff0000')
line.set(df.rename(columns={'value':'Test'}))
chart.load()
print(chart._html[:12000])
