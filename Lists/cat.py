file=open("Adj_cat.txt","r")
words=[]
for i in file.readlines():
    words.append(i.replace("},","}"))

for i in words:
    i=eval(i)
    #print(i)
    if i["temperature"]=="hot" or i["wetness"]=="dry":
        print(i["word"])