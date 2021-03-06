from zipfile import ZipFile

with ZipFile('strategy.zip', 'w') as out:
    out.write('geometry.py')
    out.write('utils.py')
    out.write('constants.py')
    out.write('assessments.py')
    out.write('prediction.py')
    out.write('MyStrategy.py')