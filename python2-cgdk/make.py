from zipfile import ZipFile

with ZipFile('strategy.zip', 'w') as out:
    out.write('geometry.py')
    out.write('MyStrategy.py')