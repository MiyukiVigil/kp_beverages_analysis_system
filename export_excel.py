import pandas as pd

def export_excel(data, path):
    df = pd.DataFrame(data)
    df.to_excel(path, index=False)