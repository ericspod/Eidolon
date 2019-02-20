
print('Name:',__name__)

if __name__=='builtins':
    print('Builtins namespace')
elif __name__=='__main__':
    print('Script')
else:
    print('Imported')

#print(dir())