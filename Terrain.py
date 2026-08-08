from logging import root

from qgis.PyQt.QtCore import(QVariant,Qt)
from qgis.core import (QgsSpatialIndex,QgsFeatureRequest,QgsProject)
import time
import random
import processing
import numpy as np
import os
from qgis.PyQt.QtWidgets import (QInputDialog,QDialog,QVBoxLayout,QLabel,QSlider,QPushButton,QHBoxLayout)
from qgis.PyQt.QtCore import Qt
from superqt import QRangeSlider

number=str(random.randint(0,9999999999999999)) #run id appended to outputs

desertmode=False

class TerrainDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terrain Ranges")
        layout = QVBoxLayout()
        self.sliders = {}
        '''
        defaults=[{"feature":"Lakes","min":0,"max":10},
                  {"feature":"Farms","min":10,"max":20},
                  {"feature":"Villages","min":20,"max":30},
                  {"feature":"Forests","min":30,"max":50},
                  {"feature":"Shrines","min":30,"max":100},
                  {"feature":"Mountains","min":60,"max":100},
                  {"feature":"Desert","min":0,"max":10}]
        '''
        
        defaults=[{"feature":"Lakes","min":0,"max":5},
                          {"feature":"Farms","min":30,"max":50},
                          {"feature":"Villages","min":5,"max":30},
                          {"feature":"Forests","min":50,"max":70},
                          {"feature":"Shrines","min":95,"max":100},
                          {"feature":"Mountains","min":70,"max":100},
                          {"feature":"Magical Lands","min":-2,"max":-1},
                          {"feature":"Desert","min":80,"max":100}]
                
        for i in defaults:
            label = QLabel(f'{i["feature"]}: {i["min"]}–{i["max"]}%')
            slider = QRangeSlider(Qt.Orientation.Horizontal)
            slider.setRange(-2, 100)
            slider.setValue((i["min"], i["max"]))
            low, high = slider.value()
            slider.valueChanged.connect(lambda v, l=label, n=i["feature"]:l.setText(f"{n}: {v}%"))
            layout.addWidget(label)
            layout.addWidget(slider)
            self.sliders[i["feature"]] = slider
        buttons = QHBoxLayout()
        ok = QPushButton("OK")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.setLayout(layout)
dlg = TerrainDialog()

if dlg.exec():
    ranges = {key: slider.value() for key, slider in dlg.sliders.items()}
else:
    raise Exception("Cancelled")


def makepath(name,ext="gpkg"):
    path = os.path.dirname(QgsProject.instance().fileName())
    if ext=="gpkg" or ext=="shp":
        return os.path.join(path, f"{name}_{number}.{ext}")
    elif ext=="txt" or ext=="csv":
        return os.path.join(path, "Lists", f"{name}.{ext}")
    else:
        return os.path.join(path, f"{name}.{ext}")

def makelayer(path,layername,style=None):
    return iface.addVectorLayer(makepath(path), f"{layername}_{number}", "ogr")

def paint(Layer,style):
    Layer.loadNamedStyle(makepath(style,"qml"))
    Layer.triggerRepaint()

layer=iface.activeLayer() #select island layer  
island_id=layer.id()


processing.run("native:savefeatures",
               {"INPUT": layer,
                "OUTPUT": makepath("island")}) #save island layer and remove temporary output
QgsProject.instance().removeMapLayer(iface.activeLayer().id())
layer=makelayer("island", 'Island')
paint(layer,"Seeds")
layer=iface.activeLayer()

layer.startEditing()
#layer.loadNamedStyle(makepath("Seeds","qml"))
#layer.triggerRepaint()


def getwords(filename):
    List=[]
    file=open(makepath(filename,"txt"))
    for i in file.readlines():
        List.append(str(i).replace("\n",""))
    return List

def getcatwords(filename,temp,wet):
    List=[]
    file=open(makepath(filename,"txt"))
    for i in file.readlines():
        i=eval(i.replace("},","}"))
        if i["temperature"]==temp or i["wetness"]==wet:
            List.append(i["word"])
    return List

adverbs=getwords("Adverbs")
adjectives=getwords("Adjectives")
dry_adjectives=getcatwords("Adj_cat","hot","dry")
titles=getwords("Titles")
amenities=getwords("Amenities")
names=getwords("Names")
peasants=getwords("PeasantTitles")
citytypes=getwords("CityTypes")
sites=getwords("Shrines")
foresttypes=getwords("Trees")
shipnames=getwords("Ships")
laketypes=getwords("LakeTypes")
ofs=getwords("ofs")
farmtypes=getwords("FarmTypes")
animals=getwords("Animals")
seatypes=getwords("SeaTypes")
fairytypes=getwords("Fairies")
swamps=getwords("Swamps")
roads=getwords("Roads")
saints=getwords("Saints")
quarrytypes=getwords("QuarryTypes")
res=getwords("Resources")


#terrain mode
options = ["Rise from peaks","Descend from peaks","Jiggle around peaks"]

choice, ok = QInputDialog.getItem(
    None,
    "Terrain Generation",
    "Terrain mode:",
    options,
    editable=False)

if not ok:
    raise Exception("User cancelled")

mode = options.index(choice) + 1



terrainheights=[]

areas=[]
for f in layer.getFeatures():
    areas.append(f.geometry().area())




def getheight(feature):

    #print(percs[ranges[feature][0]],percs[ranges[feature][1]])
    if ranges[feature][1] <= -1:
        return (-1,-1)
    else:
        return percs[ranges[feature][0]],percs[ranges[feature][1]]

def checkheight(feature):
    if getheight(feature)[1] <= -1:
        return False
    else:
        return True
    
def gen_terrain(): #calculate terrain
    global percs
    global layer
    
    print("Terrain")
    
  
    
    index = QgsSpatialIndex(layer.getFeatures())
    attempts=0
    
    while True:
        attempts+=1
        heights=[]
        changed = False
        for f in layer.getFeatures():
            heights.append(f["Height"])
            if f["Height"] == 0: #don't try to start from zero height shape'
                continue

            geom = f.geometry()
            
            for fid in index.intersects(geom.boundingBox()): #build spatial index
                if fid == f.id(): # is not itself
                    continue

                n = layer.getFeature(fid)

                if n["Height"] != 0: #ignore shapes with zero height
                    continue

                if not geom.touches(n.geometry()): #ignore shapes that don't touch parent feature'
                    continue

                jiggle = f["Height"] * random.uniform(0, 0.2) #random number between 0 and 20% of the parent height

                if mode == 1:  #rise from peaks
                    n["Height"] = f["Height"] + jiggle
                elif mode == 2: #descend from peaks
                    n["Height"] = f["Height"] - jiggle
                else: #jiggle around peaks
                    n["Height"] = random.uniform(f["Height"] - jiggle,
                                                f["Height"] + jiggle)
                layer.updateFeature(n)
                changed = True
            
        print(f"Attempts: {attempts}, Zero heights: { int(heights.count(0) / layer.featureCount() * 100)}%")
        if attempts > 1000:
            break
        if not changed:
            break                                                                                                                                                                                                                                                                                                                               
    layer.commitChanges()

    
    for f in layer.getFeatures():
        terrainheights.append(f["Height"])
    percs=np.percentile(terrainheights,np.arange(101))

    #buf=processing.run("native:buffer",
    #                    {'INPUT':layer,'DISTANCE':50,'SEGMENTS':50,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,#'SEPARATE_DISJOINT':False,'OUTPUT':'TEMPORARY_OUTPUT'})
    #smooth=processing.run("native:smoothgeometry",
    #                       {'INPUT':buf['OUTPUT'],'ITERATIONS':10,'OFFSET':0.25,'MAX_ANGLE':180,'OUTPUT':makepath("smooth")})
    #smooth_layer=iface.addVectorLayer(makepath("smooth"), "Smoothed", "ogr")

    paint(layer,"Island")
    #paint(smooth_layer,"Island")

Raster=makepath("Raster", "tif")
slope_layer=makepath("Slope", "tif")
Trees=makepath("Trees")

def make_raster(): #generate DTM
    
    processing.run("gdal:rasterize", 
    {'INPUT':layer,
    'FIELD':'Height',
    'BURN':0,
    'USE_Z':False,
    'UNITS':0,
    'WIDTH':250,
    'HEIGHT':250,
    'EXTENT':None,
    'NODATA':None,
    'CREATION_OPTIONS':None,
    'DATA_TYPE':5,
    'INIT':None,
    'INVERT':False,
    'EXTRA':'',
    'OUTPUT':Raster})
    #iface.addRasterLayer(Raster, "Height", "gdal")   
   
def slope(): #calculate slope
    processing.run("native:slope", 
    {'INPUT':Raster,
    'Z_FACTOR':0.01,
    'NODATA':-9999,
    'CREATION_OPTIONS':None,
    'OUTPUT':makepath("Slope", "tif")})
    slopelayer=iface.addRasterLayer(makepath("Slope", "tif"), f"Slope_{number}", "gdal")
    paint(slopelayer,"Slope")

def copy(copyname,style): #copy layer and apply a different style
    processing.run("native:savefeatures",{"INPUT":layer,"OUTPUT": makepath(copyname,"gpkg")})
    #iface.addVectorLayer(makepath(copyname),copyname,"ogr")
    copied=makelayer(copyname,copyname)
    paint(copied,style)
    
    
    
def trees(): #generate forests
    print("Trees")
    if checkheight("Forests")==True:
        

        trees=processing.run("native:extractbyexpression", 
        {'INPUT':layer,'EXPRESSION':f'"Height">={getheight("Forests")[0]} and "Height"<={getheight("Forests")[1]}','OUTPUT':'TEMPORARY_OUTPUT'})

        
        
        dissolved=processing.run("native:dissolve", 
        {'INPUT':trees['OUTPUT'],
        'FIELD':[],
        'SEPARATE_DISJOINT':True,
        'OUTPUT':makepath("trees_dissolve")})
        
        try:
            processing.run("native:randomextract", 
                        {'INPUT':dissolved['OUTPUT'],
                            'METHOD':0,
                            'NUMBER':n,
                            'OUTPUT':makepath("trees")})
            trees=makelayer("trees", "Trees")
            #trees=iface.addVectorLayer(makepath("trees"), "Trees", "ogr")
        except:
            trees=makelayer("trees_dissolve", "Trees")
            #trees=iface.addVectorLayer(makepath("trees_dissolve"), "Trees", "ogr")
                                                                                                                                                
        
            
        
        
        trees.startEditing()
        trees.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        trees.updateFields()
        trees.startEditing()
        
        for f in trees.getFeatures():
            n=random.randint(1,3)
            ftype=random.choice(foresttypes)
            vowels=['a','e','i','o','u','y']
            of=random.choice(ofs)
            if n==1:
                
            
                if 'O' in of.upper()[0]:
                    f["Name"]=f"{random.choice(adverbs)} {random.choice(adjectives)} {ftype} {of} {name('Villages')}"
                else:
                    f["Name"]=f"{ftype}{random.choice(vowels)}{random.choice(vowels)} {of} {name('Villages')}"
            elif n==2:
                of=random.choice(["of","o'"])
                f["Name"]=f"{random.choice(adverbs)} {random.choice(adjectives)} {ftype} {of} {name('Villages')}"
            else:
                f["Name"]=f"{name('Villages')} {ftype}"
            trees.updateFeature(f)
        trees.commitChanges()
        paint(trees,"Trees")
        #trees.loadNamedStyle(makepath("Trees","qml"))
        #trees.triggerRepaint()
  
def make_desert(): #generate forests
    if checkheight("Desert")==True:
        print("Desert")
        
        
        extract=processing.run("native:extractbyexpression", 
        {'INPUT':layer,'EXPRESSION':f'"Height">={getheight("Desert")[0]} and "Height"<={getheight("Desert")[1]}','OUTPUT':'TEMPORARY_OUTPUT'})


        dissolved=processing.run("native:dissolve", 
            {'INPUT':extract['OUTPUT'],
            'FIELD':[],
            'SEPARATE_DISJOINT':True,
            'OUTPUT':makepath("Desert")})
    
        
        desert=makelayer("Desert", "Desert")                                                                                                                             
        desert.startEditing()
        desert.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        desert.updateFields()
        desert.startEditing()
        
        for f in desert.getFeatures():
            n=random.randint(1,5)
            if n==1:
            
                f["Name"]=f"{random.choice(adverbs)} {random.choice(adjectives)} Desert {random.choice(ofs)} {name('Villages')}"
            else:
                f["Name"]=f"{name('Villages')} Desert"
            desert.updateFeature(f)
        desert.commitChanges()
        paint(desert,"Desert")

def make_fairies():
    if checkheight("Magical Lands")==True:
        print("Fairies")
        
        extract=processing.run("native:extractbyexpression", 
        {'INPUT':layer,'EXPRESSION':f'"Height">={getheight("Magical Lands")[0]} and "Height"<={getheight("Magical Lands")[1]}','OUTPUT':'TEMPORARY_OUTPUT'})

        
        
        dissolved=processing.run("native:dissolve", 
        {'INPUT':extract['OUTPUT'],
        'FIELD':[],
        'SEPARATE_DISJOINT':True,
        'OUTPUT':makepath("fairies_dissolve")})
        
        try:
            processing.run("native:randomextract", 
                        {'INPUT':dissolved['OUTPUT'],
                            'METHOD':0,
                            'NUMBER':2,
                            'OUTPUT':makepath("fairylands")})
            fairies=makelayer("fairylands", "Magical Lands")
        except:
            fairies=makelayer("fairies_dissolve", "Magical Lands")                                                        
        
            

        fairies.startEditing()
        fairies.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        fairies.updateFields()
        fairies.startEditing()
        
        for f in fairies.getFeatures():
            n=random.randint(1,2)
            if n==1:
                f["Name"]=f"{random.choice(fairytypes)} Lands of {name("Villages")}"
            elif n==2:                                                      
                f["Name"]=f" {random.choice(adjectives)} {random.choice(fairytypes)} Lands"
            
            fairies.updateFeature(f)
        fairies.commitChanges()
        paint(fairies,"Fairies")
def noise():
    print("Noise")
    copy("Noise","Noise")    
    
def label():      
    global islandname                                                                                                    
    print("Label")
    fixed = processing.run("native:fixgeometries",
        {'INPUT': layer,
        'OUTPUT': 'TEMPORARY_OUTPUT'})

    dissolved=processing.run("native:dissolve", 
    {'INPUT':fixed['OUTPUT'],'FIELD':[],
    'SEPARATE_DISJOINT':False,
    'OUTPUT':makepath("Beach", "shp")})

    
    processing.run("native:polygonstolines", 
    {'INPUT':dissolved['OUTPUT'],
    'OUTPUT':makepath("Island_label_line")})
    
    #island=iface.addVectorLayer(makepath("Island_label_line"), "label", "ogr")

    #island = QgsVectorLayer(makepath("Island_label_line"), "label", "ogr")
    island=makelayer("Island_label_line", "Label")
    #QgsProject.instance().addMapLayer(island, False)  # Don't add to root
    
    island.startEditing()
    island.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
    island.updateFields()
    islands=["Island","Isle", "Islet","Insel","Isla","Islae","Islettes", "Rock","Atoll","Islandia","Ilando","Islo","Islote","Islitas","Islotee","Islotes","Islotees"]
    for f in island.getFeatures():
        n=random.randint(1,5)
        if n==1:
            islandname=f'{random.choice(adverbs)} {random.choice(adjectives)} {random.choice(islands)} {random.choice(ofs)} {name("Islands")}'
        elif n==2:
            islandname=f'{random.choice(adjectives)} {random.choice(islands)} {random.choice(ofs)} {name("Islands")}'
        elif n==3:
            islandname=f'{random.choice(islands)} {random.choice(ofs)} {name("Islands")}'
        elif n==4:
            islandname=f'{name("Islands")} {random.choice(islands)}'
        elif n==5:
            islandname=f'{random.choice(islands)} {random.choice(ofs)} {random.choice(saints)} {name("Islands")}'
        f["Name"]=islandname
        island.updateFeature(f)
    island.commitChanges()

   
    paint(island,"Island_Labels")


    
    

def sea():
    print("Sea")
    bounds=processing.run("native:minimumboundinggeometry", 
                   {'INPUT':layer,
                    'FIELD':None,
                    'TYPE':1,
                    'OUTPUT':'TEMPORARY_OUTPUT'})
    
    
    diff=processing.run("native:difference", 
                   {'INPUT':bounds['OUTPUT'],
                    'OVERLAY':layer,
                    'OUTPUT':'TEMPORARY_OUTPUT',
                    'GRID_SIZE':None})

    single=processing.run("native:multiparttosingleparts", 
                   {'INPUT':diff['OUTPUT'],
                   'OUTPUT':'TEMPORARY_OUTPUT'})
    
    
    buffer=processing.run("native:buffer",
                    {'INPUT':single['OUTPUT'],
                     'DISTANCE':-1,
                     'SEGMENTS':5,
                     'END_CAP_STYLE':0,
                     'JOIN_STYLE':0,
                     'MITER_LIMIT':2,
                     'DISSOLVE':False,
                     'SEPARATE_DISJOINT':False,
                     'OUTPUT':'TEMPORARY_OUTPUT'})
    
    processing.run("native:multiparttosingleparts", 
                   {'INPUT':buffer['OUTPUT'],
                    'OUTPUT':makepath("sea")})
    
    
    sea=makelayer("sea", "Sea")
    paint(sea,"Sea")
    
    sea.startEditing()
    sea.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
    sea.dataProvider().addAttributes([QgsField("Area", QVariant.Double)])
    sea.dataProvider().addAttributes([QgsField("ShipName", QVariant.String)])
    sea.dataProvider().addAttributes([QgsField("Colour", QVariant.Int)])
    sea.dataProvider().addAttributes([QgsField("Side", QVariant.Int)])
    
    


    sea.updateFields()
   
    for f in sea.getFeatures():
        Area=f.geometry().area()
        f["Name"]=name('Villages')
        f["ShipName"]=name('Villages')
        f["Colour"]=random.randint(0,360)
        sea.updateFeature(f)
    

    
    
    for f in sea.getFeatures():
        
        water_name=name("Oceans").upper()
        #f["Name"]=f'{name("Oceans")} {random.choice(types)}'
        f["Name"]=random.choice([f"{water_name} {random.choice(seatypes)}", 
                                 f"{random.choice(seatypes)} {random.choice(ofs)} {water_name}"])
                                 
        f["ShipName"]=random.choice([
            f"{random.choice(adjectives)} {random.choice(shipnames)} {random.choice(ofs)} {name('Villages')}",
            f"{random.choice(shipnames)} {random.choice(ofs)} {name('Villages')}",
            f"{name('Villages')} {random.choice(shipnames)}"])
        
        sea.updateFeature(f)
    sea.commitChanges()

    
def mountains():
    if checkheight("Mountains")==True:
        print("Mountains")
        heights=[]
        
        
        
        
        mounts=processing.run("native:extractbyexpression", 
        {'INPUT':layer,
        'EXPRESSION':f'"Height">={getheight("Mountains")[0]} and "Height"<={getheight("Mountains")[1]}',
        'OUTPUT':makepath("quarries")})
        quarries=makelayer("quarries", "Quarries")
        paint(quarries,"Quarries")

        quarries.startEditing()
        quarries.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        quarries.updateFields()
        for f in quarries.getFeatures():
            f["Name"]=f"{random.choice(adjectives)} {random.choice(res)} {random.choice(quarrytypes)} of {name('Villages')}"
            quarries.updateFeature(f)
        quarries.commitChanges()
            


        dissolved=processing.run("native:dissolve", 
        {'INPUT':mounts['OUTPUT'],
        'FIELD':[],
        'SEPARATE_DISJOINT':True,
        'OUTPUT':makepath("Mountains")})

        
    
        
        mount=makelayer("Mountains", "Mountains")
        
        mount.startEditing()
        mount.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        mount.dataProvider().addAttributes([QgsField("QuarryName", QVariant.String)])
        mount.updateFields()
        mount.startEditing()


        
        for f in mount.getFeatures():
            
            mname=name("Mountains")
            f["Name"]=random.choice([f"{mname} Mountain",f"Mt. {mname}",])
            f["QuarryName"]=f"{random.choice(adjectives)} {random.choice(res)} {random.choice(quarrytypes)} of {name('Villages')}"
            
            mount.updateFeature(f)
        mount.commitChanges()
        paint(mount,"Mountain")

        peak=processing.run("native:extractbyexpression", 
            {'INPUT':layer,
            'EXPRESSION':f'"Height">={percs[98]} ',
            'OUTPUT':'TEMPORARY_OUTPUT'})

        mountain_path=processing.run("native:shortestline", 
                                    {'SOURCE':peak['OUTPUT'],'DESTINATION':makepath("onlycities","shp"),'METHOD':1,'NEIGHBORS':1,'DISTANCE':2000,'OUTPUT':makepath("mountain_paths", "shp")})
        
        mpaths=iface.addVectorLayer(makepath("mountain_paths", "shp"), f"Mountain Paths_{number}", "ogr")
        paint(mpaths,"Mountain_Paths")
    

def make_shrines():
    '''
    while True:
        Min=random.randint(0,len(percs)-1)
        Max=random.randint(Min,len(percs))
        if Min!=Max:
            break
    '''
    if checkheight("Shrines")==True:
        print("Shrines")
        highest=processing.run("native:extractbyexpression", 
                {'INPUT':layer,
                'EXPRESSION':f'"Height">={getheight("Shrines")[0]} and "Height"<={getheight("Shrines")[1]}',
                'OUTPUT':'TEMPORARY_OUTPUT'})
        
        shrines=highest['OUTPUT']
        shrines.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        shrines.dataProvider().addAttributes([QgsField("Type", QVariant.String)])
        shrines.updateFields()
        

        shrines.startEditing()
        for f in shrines.getFeatures():
        
            t=random.choice(sites)
            f["Type"]=t
            numbers=['I','II','III','IV','V','VI','VII','VIII','IX','X']
            vars=[f"{t} {random.choice(ofs)} {random.choice(titles)} {name('Figures')}",#Statue of Lord Christ
                f"{t} {random.choice(ofs)} {random.choice(titles)} {name('Figures')}: - “{random.choice(adverbs)} {random.choice(adjectives)}”",#Statue of Lord Christ - fondly magnificent
                f"{random.choice(titles)} {name('Figures')}ʼs {t}", #Lord Christ's Statue
                f"{random.choice(adjectives)} {t}", #slippery sculpture
                f"{t} of {random.choice(titles)} {name('Figures')} the {random.choice(adjectives)}",  #Statue of Lord Christ the Incredible
                f"{t} of {random.choice(titles)} {name('Figures')} {random.choice(numbers)}"] #Statue of Queen Elizabeth II
            
            f["Name"]=random.choice(vars)
            shrines.updateFeature(f)
        shrines.commitChanges()

        numshrines=0
        for i in shrines.getFeatures():
            numshrines+=1

        if numshrines>50:
            processing.run("native:randomextract", 
                        {'INPUT':shrines,'METHOD':1,'NUMBER':5,'OUTPUT':makepath("shrines_extract")})
        else:
            processing.run("native:randomextract", 
                        {'INPUT':shrines,'METHOD':1,'NUMBER':50,'OUTPUT':makepath("shrines_extract")})
        
        shrines=makelayer("shrines_extract", "Shrines")
        paint(shrines,"Monuments")

        
def lakes():
    if checkheight("Lakes")==True:
        print("Lakes")
        
        extract=processing.run("native:extractbyexpression", 
        {'INPUT':layer,
        'EXPRESSION':f'"Height">={getheight("Lakes")[0]} and "Height"<={getheight("Lakes")[1]}',
        'OUTPUT':'TEMPORARY_OUTPUT'})
        
        
        dissolve=processing.run("native:dissolve", 
        {'INPUT':extract['OUTPUT'],
        'FIELD':[],
        'SEPARATE_DISJOINT':True,
        'OUTPUT':'TEMPORARY_OUTPUT'})

        buffer=processing.run("native:buffer",
                            {'INPUT':dissolve['OUTPUT'],'DISTANCE':10,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'SEPARATE_DISJOINT':True,'OUTPUT':'TEMPORARY_OUTPUT'})
        
        
        
        extract=processing.run("native:extractbylocation", 
        {'INPUT':buffer['OUTPUT'],
        'PREDICATE':[2],
        'INTERSECT':makepath("sea"),
        'OUTPUT':makepath("lakes", "shp")})

        
        swamp=processing.run("native:extractbylocation", 
            {'INPUT':buffer['OUTPUT'],
            'PREDICATE':[0,1,4,5,6,7],
            'INTERSECT':makepath("sea"),
            'OUTPUT':makepath("swamp", "shp")})
        
        swamp=iface.addVectorLayer(makepath("swamp","shp"),f"Swamp_{number}","ogr")
        paint(swamp,"Swamp")
        swamp.startEditing()
        swamp.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        swamp.updateFields()
        for f in swamp.getFeatures():
            n=random.randint(1,3)
            if n==1:
                f["Name"]=f"{random.choice(fairytypes)} {random.choice(swamps)} of {name('Names')}"
            elif n==2:
                f["Name"]=f"{random.choice(adjectives)} {random.choice(swamps)} of {name('Names')}"
            elif n==3:
                f["Name"]=f"{random.choice(adjectives)} {random.choice(fairytypes)} {random.choice(swamps)} of {name('Names')}"
            swamp.updateFeature(f)
        swamp.commitChanges()

        lake=iface.addVectorLayer(makepath("lakes", "shp"),f"Lakes_{number}","ogr")
        lake.startEditing()
        lake.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        lake.updateFields()
        lake.startEditing()
        for f in lake.getFeatures():
            laketype=random.choice(laketypes)
        
            vars=[f"{laketype} {random.choice(ofs)} {name('Lakes')}",
                f"{laketype} {name('Lakes')}",
                f"{name('Lakes')} {laketype}",
                f"{random.choice(adjectives)} {laketype} {random.choice(ofs)} {name('Lakes')}"]
                
            f["Name"]=f"{laketype} {name('Lakes')}"
            lake.updateFeature(f)
        lake.commitChanges()
        paint(lake,"Lakes")

def rivers():
    print("Rivers")
    processing.run("native:shortestline", 
                   {'SOURCE':makepath("Mountains"),
                    'DESTINATION':makepath("sea"),
                    'METHOD':0,
                    'NEIGHBORS':1,
                    'DISTANCE':None,
                    'OUTPUT':makepath("Rivers")})
  
    rivers=makelayer("Rivers", "Rivers")
    paint(rivers,"Rivers")

def villages():
    if checkheight("Villages")==True:
        print("Villages")
        village_sizes=[]

        
        extract=processing.run("native:extractbyexpression", 
        {'INPUT':layer,'EXPRESSION':f'"Height">={getheight("Villages")[0]} and "Height"<={getheight("Villages")[1]}','OUTPUT':'TEMPORARY_OUTPUT'})

        
        dissolved=dissolve=processing.run("native:dissolve", 
        {'INPUT':extract['OUTPUT'],
        'FIELD':[],
        'SEPARATE_DISJOINT':True,
        'OUTPUT':'TEMPORARY_OUTPUT'})

        processing.run("native:smoothgeometry",
                        {'INPUT':dissolved['OUTPUT'],'ITERATIONS':10,'OFFSET':0.25,'MAX_ANGLE':180,'OUTPUT':makepath("villages","shp")})
        
        
        village=iface.addVectorLayer(makepath("villages","shp"), f"Villages_{number}", "ogr")
        
  
        village.startEditing()
        village.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        village.dataProvider().addAttributes([QgsField("Area", QVariant.Double)])
        village.dataProvider().addAttributes([QgsField("Type", QVariant.String)])
        
        village.updateFields()
        village.startEditing()
        for f in village.getFeatures():
            Area=f.geometry().area()
            f["Name"]=name('Villages')
            f["Area"] = Area
            village_sizes.append(Area)
            village.updateFeature(f)
        village.commitChanges()
        

        village.startEditing()
        areapercs = np.percentile(village_sizes, np.arange(101))

        if desertmode==True:
            adjlist=dry_adjectives
        else:
            adjlist=adjectives
        for f in village.getFeatures():
            if f["Area"]>=areapercs[80] and f["Area"]<=areapercs[90]:
                placename=f["Name"]
                f["Name"]=f"{random.choice(adjlist)} {random.choice(citytypes)} {random.choice(ofs)} {placename}".replace("\n","")
                f["Type"]='City'
            elif f["Area"]>areapercs[90]:
                placename=f["Name"]
                f["Name"]=f"{random.choice(adverbs)} {random.choice(adjlist)} {random.choice(citytypes)} {random.choice(ofs)} {placename}".replace("\n","")
                f["Type"]='Megacity'
            else:
                f["Type"]="Village"
            village.updateFeature(f)
        village.commitChanges()
        paint(village,"Villages")

        onlycities=processing.run("native:extractbyattribute", 
                    {'INPUT':village,'FIELD':'Type','OPERATOR':1,'VALUE':'Village','OUTPUT':makepath("onlycities", "shp")})
        
        
        
        centroids=processing.run("native:centroids",
        {'INPUT':village,'ALL_PARTS':False,'OUTPUT':'TEMPORARY_OUTPUT'})
        
        processing.run(
        "native:shortestline", 
        {'SOURCE':village,'DESTINATION':centroids['OUTPUT'],
        'METHOD':0,
        'NEIGHBORS':2,
        'DISTANCE':None,
        'SELF_MATCH': False,
        'OUTPUT':makepath("paths", "shp")})
        

        paths=iface.addVectorLayer(makepath("paths", "shp"),f"Paths_{number}","ogr")
    
        paint(paths,"Paths")

        paths.startEditing()
        for f in paths.getFeatures():
            f["Name"]=f"{random.choice(adjectives)} {random.choice(roads)}"
            paths.updateFeature(f)
        paths.commitChanges()
        
        places=processing.run("qgis:randompointsinsidepolygons", 
                    {'INPUT':onlycities['OUTPUT'],
                        'STRATEGY':0,
                        'VALUE':random.randint(5,20),
                        'MIN_DISTANCE':20,
                        'OUTPUT':makepath("amenities")})
        places=makelayer("amenities", "Amenities")
        places.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        places.dataProvider().addAttributes([QgsField("Type", QVariant.String)])
        places.updateFields()
        places.startEditing()
        
        for f in places.getFeatures():
            n=random.randint(1,2)
            if n==1:
                f["Name"]=f"{(random.choice(titles))} {name('Names')}ʼs {(random.choice(adjectives))} {(random.choice(amenities))}"
            else:
                f["Name"]=f"{(random.choice(adjectives))} {(random.choice(amenities))}"
            places.updateFeature(f)
        places.commitChanges()
        places.loadNamedStyle(makepath("Amenities","qml"))  
        places.triggerRepaint()
        
        processing.run("native:shortestline", 
        {'SOURCE':places,'DESTINATION':places,'METHOD':0,'NEIGHBORS':3,'DISTANCE':200,'OUTPUT':makepath("streets", "shp")})
        streets=iface.addVectorLayer(makepath("streets", "shp"),f"Streets_{number}","ogr")
        paint(streets,"Streets")


def farms():
    if checkheight("Farms")==True:
        print("Farms")
        extract=processing.run("native:extractbyexpression", 
        {'INPUT':layer,'EXPRESSION':f'"Height">={getheight("Farms")[0]} and "Height"<={getheight("Farms")[1]}','OUTPUT':'TEMPORARY_OUTPUT'})
        
        dissolve=processing.run("native:dissolve", 
        {'INPUT':extract['OUTPUT'],
        'FIELD':[],
        'SEPARATE_DISJOINT':True,
        'OUTPUT':makepath("Farms")})
        
        #farm=iface.addVectorLayer(makepath("Farms"), "Farms", "ogr"
        farm=makelayer("Farms", "Farms")
        farm.startEditing()
        farm.dataProvider().addAttributes([QgsField("Name", QVariant.String)])
        farm.updateFields()
        
        farm.startEditing()
        
        for f in farm.getFeatures():
            vars=[f"{random.choice(peasants)} {name('Names')}ʼs {random.choice(animals)} {(random.choice(farmtypes))}",
                f"{random.choice(adjectives)} {random.choice(animals)} {(random.choice(farmtypes))}",
                f"{random.choice(animals)} {(random.choice(farmtypes))}"]
            f["Name"]=random.choice(vars)
            farm.updateFeature(f)
        farm.commitChanges()
        paint(farm,"Farms")

def name(List):
    places=[]
    con=['B', 'C', 'D','F', 'G', 'H','J', 'K', 'L', 'M', 'N','P', 'Q', 'S', 'T','V', 'W', 'Y' 'Z']
    vowels=['A','E','I','O','U']
    file=open(makepath(List,"txt"))
    for name in file.readlines():
        name=name.replace("\n","")
        name=name.replace("Island","")
        name=name.replace("Isle","")
        name=name.upper()
        if len(name)>=2 and len(name)<=8:
            places.append(name)
    
    name=random.choice(places)
  
    for char in name:
        if char.upper() in vowels:
            name=name.replace(char,random.choice(vowels))
            
    for char in name:
        if char.upper() in con:
            name=name.replace(char,random.choice(con))
            break
    return str(f"{name}")
'''
def group_together():
    order=["Noise","Label","Rivers","Shrines","Streets","Amenities","Paths","Villages","Trees","Swamp","Sea","Lakes","Mountain Paths","Farms","Mountains","Quarries","Desert","Island","Slope"]


    root = QgsProject.instance().layerTreeRoot()
    group = root.insertGroup(0, islandname)
    layers = list(QgsProject.instance().mapLayers().values())
    for l in layers:
        if str(number) in l.name():
            node = root.findLayer(l.id())
            if node is None:
                continue
            old_parent = node.parent()
            layername=l.name().split("_")[0]
            print(layername)
            n=order.index(layername)
            try:
                group.insertLayer(n, l)
            except:
                group.insertLayer(-1, l)
            old_parent.removeChildNode(node)
    for i in list(QgsProject.instance().mapLayers().values()):
        if str(number) in i.name():
            i.setName(i.name().replace(f"_{number}",""))
'''
def group_together():
    order = ["Noise", "Label", "Rivers", "Shrines", "Streets", "Amenities",
        "Paths", "Villages", "Trees", "Swamp", "Lakes",
        "Mountain Paths", "Farms", "Mountains", "Quarries",
        "Desert", "Sea", "Island", "Slope"]

    root = QgsProject.instance().layerTreeRoot()
    group = root.insertGroup(0, islandname)
    layers = [
        l for l in QgsProject.instance().mapLayers().values()
        if str(number) in l.name()]

    layers.sort(
    key=lambda l: order.index(l.name().split("_")[0]
    if l.name().split("_")[0] in order
    else 0))

    
    for layer in layers:
        node = root.findLayer(layer.id())
        if node is None:
            continue
        old_parent = node.parent()
        group.addLayer(layer)
        if old_parent is not None and old_parent != group:
            old_parent.removeChildNode(node)
        layer.setName(layer.name().replace(f"_{number}", ""))
    
#flatten()
label()
gen_terrain()
make_raster()
slope()
trees()

sea()
noise()
villages()
mountains()
make_shrines()
lakes()

farms()
rivers()
make_desert()
group_together()