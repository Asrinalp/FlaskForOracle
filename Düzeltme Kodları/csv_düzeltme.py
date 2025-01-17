import pandas as pd

# CSV dosyasını oku
df = pd.read_csv('C:\\Users\\batur\\Downloads\\Consistent_INVENTORIES.csv')

df = pd.DataFrame(df, columns=['PRODUCT_ID', 'WAREHOUSE_ID', 'QUANTITY_ON_HAND'])

# Eşsiz olan değerleri bulmak için her sütun için değeri sayıyoruz
value_counts = df['QUANTITY_ON_HAND'].value_counts()

# Sadece bir kez görünen değerleri filtreliyoruz
unique_values = value_counts[value_counts != 1].index

# Sonuçları yazdırıyoruz
result = df[df['PRODUCT_ID'].isin(unique_values)]
print(result)